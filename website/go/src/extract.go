package main

import (
	"bytes"
	"database/sql"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"os"
	"strings"
	"unsafe"

	_ "github.com/lib/pq"
)

const (
	host      = "localhost"
	port      = 5432
	user      = "admin"
	dbName    = "s3loganalysis"
	batchSize = 5000
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
	// Get all s3 log names
	const logDir = "s3_logs"
	fileInfos, err := ioutil.ReadDir(logDir)
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
		s3KeyToItemId[s3Key] = fmt.Sprintf("'%d'", itemId)
	}
	err = rows.Close()
	check(err)
	fmt.Println("Done mapping keys to ids")
	// Read all files and add them to the database
	buf := &bytes.Buffer{}
	var fieldBuilder [][19]bytes.Buffer
	const insertStatement = "INSERT INTO dashboard_log (bucket, time, ip_address, requester, request_id, operation, s3_key, item_id, request_uri, http_status, error_code, bytes_sent, object_size, total_time, turn_around_time, referrer, user_agent, version_id) VALUES "
	var curBatchLogCnt int
	for _, fileInfo := range fileInfos[:10] {
		buf.Reset()
		// Get name of log file
		// String concatenation is actually fast
		buf.WriteString(logDir + "/" + fileInfo.Name())
		fileName := getBufStr(buf.Bytes())
		file, err := os.Open(fileName)
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
		addField := func(endIdx int) {
			fieldStart := lastFieldEnd
			lastFieldEnd = endIdx
			sliceStart, sliceEnd := fieldStart+1, endIdx
			if fieldIsEscaped {
				sliceStart++
				sliceEnd--
			}
			field := getBufStr(buf.Bytes()[sliceStart:sliceEnd])
			fieldIsEscaped = false
			//fmt.Printf("%d, %s\n", fieldIdx, field)
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
			case 1, 3, 4, 5, 6, 8, 9, 10, 11, 14, 15, 16, 17:
				if field == "-" {
					fieldBuilder[curBatchLogCnt][fieldIdx].WriteString("NULL")
				} else {
					builder := &fieldBuilder[curBatchLogCnt][fieldIdx]
					builder.WriteString("'")
					builder.WriteString(field)
					builder.WriteString("'")
				}
				fieldIdx++
				break
			case 7:
				if field == "-" {
					fieldBuilder[curBatchLogCnt][fieldIdx].WriteString("NULL")
					fieldBuilder[curBatchLogCnt][fieldIdx+1].WriteString("NULL")
				} else {
					builder := &fieldBuilder[curBatchLogCnt][fieldIdx]
					builder.WriteString("'")
					builder.WriteString(field)
					builder.WriteString("'")
					fieldBuilder[curBatchLogCnt][fieldIdx+1].WriteString(s3KeyToItemId[field])
				}
				fieldIdx += 2
				break
			case 2:
				if field == "-" {
					fieldBuilder[curBatchLogCnt][fieldIdx].WriteString("NULL")
				} else {
					builder := &fieldBuilder[curBatchLogCnt][fieldIdx]
					builder.WriteString("to_timestamp('" + field + "','DD/Mon/YYYY:HH24:MI:SS')")
					builder.WriteString(field)
					builder.WriteString("','DD/Mon/YYYY:HH24:MI:SS')")
				}
				fieldIdx++
				break
			}
			logFieldIdx++
		}
		for charIdx, char := range fileContent {
			if char == '[' || char == ']' || char == '"' { // Escape special strings with spaces and timestamps
				inEscaped = !inEscaped
				fieldIsEscaped = true
			} else if char == '\n' { // Move onto another log instance
				addField(charIdx)
				for fieldIdx < len(fieldBuilder) {
					fieldIdx++
					fieldBuilder[curBatchLogCnt][fieldIdx].WriteString("NULL")
				}
				fieldIdx = 0
				logFieldIdx = 0
				curBatchLogCnt++
				if curBatchLogCnt == 5 {
					var query [][19]string
					for logIdx := 0; logIdx < 5; logIdx++ {
						query = append(query, [19]string{})
						for fieldIdx, builder := range fieldBuilder[curBatchLogCnt] {
							query[logIdx][fieldIdx] = getBufStr(builder.Bytes())
						}
					}
					//query := strings.Join("(" + strings.Join(fields[:], ",") + ")", ",")s
					//for _, builder := range fieldBuilder {
					//	builder.Reset()
					//}
					//fmt.Println(query)
					//_, err = db.Exec(query)
					//check(err)
					//fmt.Println(query)
					//curBatchLogCnt = 0
					//queryBuilder.Reset()
					//queryBuilder.WriteString(insertStatement)
				}
			} else if char == ' ' && !inEscaped { // We are ending a field definition
				addField(charIdx)
			}
		}
	}
	err = db.Close()
	check(err)
}
