package main

import (
	"bytes"
	"fmt"
	"io"
	"io/ioutil"
	"os"
	"strings"
)

func main() {
	//db, err := sql.Open("sqlite3", "db.sqlite3")'
	const logDir = "s3_logs"
	fileInfos, _ := ioutil.ReadDir(logDir)
	var sb strings.Builder
	buf := bytes.NewBuffer(nil)
	for _, fileInfo := range fileInfos {
		sb.Reset()
		sb.WriteString(logDir)
		sb.WriteString("/")
		sb.WriteString(fileInfo.Name())
		file, _ := os.Open(sb.String())
		buf.Reset()
		_, _ = io.Copy(buf, file)
		_ = file.Close()
		sb.Reset()
		sb.Write(buf.Bytes())
		fmt.Println(sb.String())
	}
}
