package main

import (
	"bytes"
	"database/sql"
	"fmt"
	"github.com/cheggaaa/pb"
	"github.com/karrick/godirwalk"
	"io"
	"io/ioutil"
	"log"
	"os"
	"runtime"
	"strconv"
	"strings"
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
	buf := &bytes.Buffer{}
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
		check(err)
		batchLogIdx = 0
		runtime.GC()
	}
	// Get all s3 log names
	const logDirName = "s3_logs"
	logDir, err := godirwalk.ReadDirents(logDirName, nil)
	check(err)
	logNames, err := godirwalk.ReadDirnames(logDirName, nil)
	check(err)
	// Progress bar
	bar := pb.New(logDir.Len()).Prefix("Files Processed:").Format(pb.FORMAT)
	bar.ManualUpdate = true
	bar.ShowElapsedTime = true
	bar.Start()
	// Walk directory
	for _, fileName := range logNames {
		buf.Reset()
		buf.WriteString(logDirName)
		buf.WriteString("/")
		buf.WriteString(fileName)
		file, err := os.Open(getBufStr(buf.Bytes()))
		check(err)
		// Copy contents of log file into buffer
		buf.Reset()
		_, err = io.Copy(buf, file)
		check(err)
		err = file.Close()
		check(err)
		fileContent := getBufStr(buf.Bytes())
		// Read log instances from file
		var logFieldIdx, fieldIdx, lastFieldEnd int
		var inEscaped, fieldIsEscaped bool
		buf.Reset()

		addField := func(endIdx int) bool {
			fieldStart := lastFieldEnd
			lastFieldEnd = endIdx
			sliceStart, sliceEnd := fieldStart+1, endIdx
			if fieldIsEscaped {
				sliceStart++
				sliceEnd--
			}
			field := getBufStr(buf.Bytes()[sliceStart:sliceEnd])
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
			if char == '[' || char == ']' || char == '"' { // Escape special strings with spaces and timestamps
				inEscaped = !inEscaped
				fieldIsEscaped = true
			} else if char == '\n' { // Move onto another log instance
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
				for idx := range fieldBuilders[:fieldIdx] {
					fieldBuilders[idx].Reset()
				}
				fieldIdx = 0
				logFieldIdx = 0
				batchLogIdx++
				if batchLogIdx == batchSize {
					batchInsert()
				}
			} else if char == ' ' && !inEscaped { // We are ending a field definition
				if !addField(charIdx) {
					// Field we do not want in the database
					for idx := range fieldBuilders[:fieldIdx] {
						fieldBuilders[idx].Reset()
					}
					fieldIdx, logFieldIdx = 0, 0
					break
				}
			}
		}

		bar.Increment()
		bar.Update()
	}
	check(err)
	bar.Finish()
	if batchLogIdx > 0 {
		batchInsert()
	}
	err = db.Close()
	check(err)
}
