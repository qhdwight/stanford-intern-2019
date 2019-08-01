package main

import (
	"bytes"
	"database/sql"
	"fmt"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/s3"
	"io/ioutil"
	"log"
	"runtime"
	"strconv"
	"strings"
	"sync"
	"time"
	"unsafe"

	_ "github.com/lib/pq"
)

const (
	host              = "localhost"
	port              = 5432
	user              = "admin"
	dbName            = "s3loganalysis"
	batchSize         = 1000
	fieldCount        = 19
	psqlNull          = "NULL"
	lasts3KeyFileName = "LastLogS3Key.txt"
)

type LogField int

// Note this should be its own block to make it start at zero properly
const (
	_ LogField = iota
	Bucket
	Time
	Ip
	Requester
	RequestId
	Operation
	S3Key
	RequestUri
	HttpStatus
	ErrorCode
	BytesSent
	ObjectSize
	TotalTime
	TurnAroundTime
	Referrer
	UserAgent
	VersionId
)

func check(err error) {
	if err != nil {
		log.Panic(err)
	}
}

func getBufStr(buf []byte) string {
	// This returns a stirng that points directly to the buffer memory, avoiding making a copy
	// This is dangerous if you change the buffer before done with the string! So be careful
	return *(*string)(unsafe.Pointer(&buf))
}

func getDbPassword() string {
	content, err := ioutil.ReadFile(".env")
	check(err)
	var password string
	for _, line := range strings.Split(string(content), "\n") {
		if strings.HasPrefix(line, "PG_ADMIN_PASSWORD") {
			password = line[strings.Index(line, "=")+1:]
		}
	}
	return password
}

func main() {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String("us-west-2"),
	})
	check(err)
	s3c := s3.New(sess)
	bucket := aws.String("encode-public-logs")
	logMtx := &sync.Mutex{}
	// Make a reasonably sized buffer to start to avoid constant resizing in the beginning
	logBuf := bytes.NewBuffer(make([]byte, 0, 100000000))

	// Open connection to database, read password from .env file
	password := getDbPassword()
	psqlLoginInfo := fmt.Sprintf(
		"host=%s port=%d user=%s password=%s dbname=%s sslmode=disable",
		host, port, user, password, dbName,
	)
	db, err := sql.Open("postgres", psqlLoginInfo)
	check(err)

	// Make a dictionary to map s3 keys to item ids to prevent excessive database queries
	rows, err := db.Query("SELECT s3_key, id FROM dashboard_item")
	check(err)
	s3KeyToItemId := map[string]string{} // Similar to a dictionary that maps a string to a string in Python
	// We are mapping S3 keys to their item IDs via the Item table so we can quickly look it up in-memory later when we create logs
	for rows.Next() {
		var s3Key string
		var itemId int
		// Drop into Go variables from PSQL query result in order
		err = rows.Scan(&s3Key, &itemId)
		check(err)
		// Quotes are important since all PSQL variables need to be wrapped in them, even numbers
		s3KeyToItemId[s3Key] = "'" + strconv.Itoa(itemId) + "'"
	}
	err = rows.Close()
	check(err)

	fieldBuilders := [fieldCount]bytes.Buffer{}
	rowBuilders := make([]bytes.Buffer, 0, batchSize)
	const insertStatement = "INSERT INTO dashboard_log (bucket, time, ip_address, requester, requester_type, request_id, operation, s3_key, item_id, request_uri, http_status, error_code, bytes_sent, object_size, total_time, turn_around_time, referrer, user_agent, version_id)"
	var batchLogIdx int

	batchInsert := func() {
		// We can not read an array of byte buffers directly, so we need to convert it into an array of strings
		// They will still be pointing into initial byte buffers to save memory, we just need Go to recognize them as strings instead of bytes
		rows := make([]string, len(rowBuilders))
		for rowIdx, rowBuilder := range rowBuilders {
			rows[rowIdx] = getBufStr(rowBuilder.Bytes())
		}
		query := insertStatement + " VALUES " + strings.Join(rows, ",")
		for _, rowBuilder := range rowBuilders {
			rowBuilder.Reset()
		}
		// Reset slice to zero length. This does not free the other memory, which is what we want so we do not have to allocate later!
		rowBuilders = rowBuilders[:0]
		_, err = db.Exec(query)
		fmt.Println("Inserted into db")
		check(err)
		batchLogIdx = 0
		// We created a bunch of stuff on the heap so now is a good time to GC
		runtime.GC()
	}
	// We use the last key read to start reading everything after it
	// Logs are constant so nothing before the last read log changes - we only need to extract the new logs
	lastKeyBytes, err := ioutil.ReadFile(lasts3KeyFileName)
	check(err)
	lastKey := getBufStr(lastKeyBytes)
	fmt.Println("Using", lastKey, "as last S3 key to start after")

	err = s3c.ListObjectsV2Pages(
		&s3.ListObjectsV2Input{
			Bucket:     bucket,
			StartAfter: aws.String(lastKey),
			MaxKeys:    aws.Int64(1000), // 1000 is the maximum
		},
		func(page *s3.ListObjectsV2Output, lastPage bool) bool {
			// This channel represents how many workers are available
			// The actual value of the boolean doesn't matter, just whether it exists in the channel
			// TODO change to struct{} instead of bool to avoid confusion since value does not matter
			worker := make(chan bool, 20)
			// Fill up the worker pool initially
			for i := 0; i < cap(worker); i++ {
				worker <- true
			}
			// A wait group is basically an atomic counter. You can wait until the counter reaches zero, or when we have read all logs.
			wg := &sync.WaitGroup{}
			wg.Add(len(page.Contents))
			objIdx := 0
			now := time.Now()
			for {
				<-worker
				if objIdx == len(page.Contents) {
					// We are done with all logs. Note that objIdx is a copy so no thread safety issues
					break
				}
				go func(idx int, obj *s3.Object) {
					//gs := time.Now()
					resp, err := s3c.GetObject(&s3.GetObjectInput{
						Bucket: bucket,
						Key:    obj.Key,
					})
					check(err)
					//fmt.Println("Get: ", time.Since(gs))

					//rs := time.Now()
					logMtx.Lock()                       // We use one buffer so make sure to lock it when writing to it
					_, err = logBuf.ReadFrom(resp.Body) // Copy from HTTP response into our buffer
					check(err)
					logMtx.Unlock()
					//fmt.Println("Read: ", time.Since(rs))

					err = resp.Body.Close()
					check(err)

					worker <- true // Return this worker to the pool
					wg.Done()      // Essentially decrements atomic counter by one
				}(objIdx, page.Contents[objIdx])
				objIdx += 1
			}
			wg.Wait() // Wait until wait group is done - counter reaches zero
			fmt.Println(len(page.Contents), "Files Downloaded in", time.Since(now))

			now = time.Now()
			fileContent := getBufStr(logBuf.Bytes())
			var logFieldIdx, fieldIdx, lastFieldEnd int
			var inEscaped, fieldIsEscaped, skipThisLine bool

			addField := func(endIdx int) bool {
				fieldStart := lastFieldEnd
				lastFieldEnd = endIdx
				sliceStart, sliceEnd := fieldStart+1, endIdx
				if fieldIsEscaped {
					sliceStart++
					sliceEnd--
				}
				field := getBufStr(logBuf.Bytes()[sliceStart:sliceEnd])
				fieldIsEscaped = false
				switch LogField(logFieldIdx) {
				case Bucket, Ip, RequestId, RequestUri, HttpStatus, ErrorCode, BytesSent, ObjectSize, TotalTime, TurnAroundTime, Referrer, UserAgent, VersionId:
					// TODO make function which retrieves next and automatically increments field index
					fieldBuilder := &fieldBuilders[fieldIdx]
					if field == "-" {
						fieldBuilder.WriteString(psqlNull)
					} else {
						fieldBuilder.WriteString("'")
						fieldBuilder.WriteString(field)
						fieldBuilder.WriteString("'")
					}
					fieldIdx++
					break
				case Requester:
					fieldBuilder := &fieldBuilders[fieldIdx]
					if field == "-" {
						fieldBuilder.WriteString(psqlNull)
					} else {
						fieldBuilder.WriteString("'")
						fieldBuilder.WriteString(field)
						fieldBuilder.WriteString("'")
					}
					if strings.Contains(field, "encoded-instance") {
						fieldBuilders[fieldIdx+1].WriteString("'1'")
					} else {
						fieldBuilders[fieldIdx+1].WriteString("'0'")
					}
					fieldIdx += 2
					break
				case Operation:
					if field == "-" {
						fieldBuilders[fieldIdx].WriteString(psqlNull)
					} else if field == "REST.GET.OBJECT" {
						fieldBuilder := &fieldBuilders[fieldIdx]
						fieldBuilder.WriteString("'")
						fieldBuilder.WriteString(field)
						fieldBuilder.WriteString("'")
					} else {
						return false
					}
					fieldIdx++
					break
				case S3Key:
					if field == "-" {
						fieldBuilders[fieldIdx].WriteString(psqlNull)
						fieldBuilders[fieldIdx+1].WriteString(psqlNull)
					} else {
						fieldBuilder := &fieldBuilders[fieldIdx]
						fieldBuilder.WriteString("'")
						fieldBuilder.WriteString(field)
						fieldBuilder.WriteString("'")
						itemId := s3KeyToItemId[field]
						if itemId == "" {
							itemId = psqlNull
						}
						fieldBuilders[fieldIdx+1].WriteString(itemId)
					}
					fieldIdx += 2
					break
				case Time:
					if field == "-" {
						fieldBuilders[fieldIdx].WriteString(psqlNull)
					} else {
						fieldBuilder := &fieldBuilders[fieldIdx]
						fieldBuilder.WriteString("to_timestamp('")
						fieldBuilder.WriteString(field)
						fieldBuilder.WriteString("','DD/Mon/YYYY:HH24:MI:SS')")
					}
					fieldIdx++
					break
				}
				logFieldIdx++
				return true
			}

			for charIdx, char := range fileContent {
				if !skipThisLine {
					if char == '[' || char == ']' || char == '"' { // Escape special strings with spaces and timestamps
						inEscaped = !inEscaped
						fieldIsEscaped = true
					} else if char == '\n' { // Move onto another log instance
						if skipThisLine {
							skipThisLine = false
						}
						rowBuilders = append(rowBuilders, bytes.Buffer{})
						addField(charIdx)
						for fieldIdx < fieldCount-1 {
							fieldIdx++
							fieldBuilders[fieldIdx].WriteString(psqlNull)
						}
						rowBuilder := &rowBuilders[batchLogIdx]
						var row [fieldCount]string
						for idx := range fieldBuilders {
							row[idx] = getBufStr(fieldBuilders[idx].Bytes())
						}
						rowBuilder.WriteString("(")
						rowBuilder.WriteString(strings.Join(row[:], ","))
						rowBuilder.WriteString(")")
						for idx := range fieldBuilders {
							fieldBuilders[idx].Reset()
						}
						fieldIdx, logFieldIdx = 0, 0
						batchLogIdx++
						if batchLogIdx == batchSize {
							batchInsert()
						}
					} else if char == ' ' && !inEscaped { // We are ending a field definition
						if !addField(charIdx) {
							// Field we do not want in the database
							skipThisLine = true
						}
					}
				} else if char == '\n' {
					for idx := range fieldBuilders[:fieldIdx] {
						fieldBuilders[idx].Reset()
					}
					fieldIdx, logFieldIdx = 0, 0
					skipThisLine = false
				}
			}

			logBuf.Reset()
			fmt.Println(len(page.Contents), "Files Processed in", time.Since(now))

			if lastPage {
				// Remember last key so next time we know exactly where to find new logs
				lastKey := *page.Contents[len(page.Contents)-1].Key
				err = ioutil.WriteFile(lasts3KeyFileName, []byte(lastKey), 0777)
				check(err)
				fmt.Println("Last key scanned:", lastKey)
			}

			return true
		},
	)

	// Test if there are still some logs left
	if batchLogIdx > 0 {
		batchInsert()
	}
	err = db.Close()
	check(err)
}
