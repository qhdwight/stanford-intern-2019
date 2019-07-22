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
	host       = "localhost"
	port       = 5432
	user       = "admin"
	dbName     = "s3loganalysis"
	batchSize  = 1000
	fieldCount = 18
	psqlNull   = "NULL"
)

func check(err error) {
	if err != nil {
		log.Panic(err)
	}
}

func getBufStr(buf []byte) string {
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
	rows, err := db.Query("SELECT dashboard_item.s3_key, dashboard_item.id FROM dashboard_item")
	check(err)
	s3KeyToItemId := map[string]string{}
	for rows.Next() {
		var s3Key string
		var itemId int
		err = rows.Scan(&s3Key, &itemId)
		check(err)
		s3KeyToItemId[s3Key] = "'" + strconv.Itoa(itemId) + "'"
	}
	err = rows.Close()
	check(err)

	// Read all files and add them to the database
	fieldBuilders := [fieldCount]bytes.Buffer{}
	rowBuilders := make([]bytes.Buffer, 0, batchSize)
	const insertStatement = "INSERT INTO dashboard_log (bucket, time, ip_address, requester, request_id, operation, s3_key, item_id, request_uri, http_status, error_code, bytes_sent, object_size, total_time, turn_around_time, referrer, user_agent, version_id) VALUES "
	var batchLogIdx int

	batchInsert := func() {
		rows := make([]string, len(rowBuilders))
		for rowIdx, rowBuilder := range rowBuilders {
			rows[rowIdx] = getBufStr(rowBuilder.Bytes())
		}
		query := insertStatement + strings.Join(rows, ",")
		for _, rowBuilder := range rowBuilders {
			rowBuilder.Reset()
		}
		rowBuilders = rowBuilders[:0]
		_, err = db.Exec(query)
		fmt.Println("Inserted into db")
		//fmt.Println(query)
		check(err)
		batchLogIdx = 0
		runtime.GC()
	}

	err = s3c.ListObjectsV2Pages(
		&s3.ListObjectsV2Input{
			Bucket:  bucket,
			Prefix:  aws.String("2019-07-21"),
			MaxKeys: aws.Int64(1000),
		},
		func(page *s3.ListObjectsV2Output, lastPage bool) bool {
			worker := make(chan bool, 20)
			for i := 0; i < cap(worker); i++ {
				worker <- true
			}
			wg := &sync.WaitGroup{}
			wg.Add(len(page.Contents))
			objIdx := 0
			now := time.Now()
			for {
				<-worker
				if objIdx == len(page.Contents) {
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
					logMtx.Lock()
					_, err = logBuf.ReadFrom(resp.Body)
					check(err)
					logMtx.Unlock()
					//fmt.Println("Read: ", time.Since(rs))

					err = resp.Body.Close()
					check(err)
					worker <- true
					wg.Done()
				}(objIdx, page.Contents[objIdx])
				objIdx += 1
			}
			wg.Wait()
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
				switch logFieldIdx {
				// 0: Bucket Owner (Ignored)
				// 1: Bucket
				// 2: Time
				// 3: IP
				// 4: Requester
				// 5: Request ID
				// 6: Operation
				// 7: Key
				// 8: URI
				// 9: HTTP Status
				// 10: Error Code
				// 11: Bytes Sent
				// 12: Object Size
				// 13: Total Time
				// 14: Turn Around Time
				// 15: Referrer
				// 16: User Agent
				// 17: Version Id
				case 1, 3, 4, 5, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17:
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
				case 6:
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
				case 7:
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
				case 2:
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
			return true
		},
	)

	if batchLogIdx > 0 {
		batchInsert()
	}
	err = db.Close()
	check(err)
}
