package main

import (
	"bytes"
	"fmt"
	"io"
	"io/ioutil"
	"log"
	"os"
	"strings"
)

func main() {
	//db, err := sql.Open("sqlite3", "db.sqlite3")
	fileNames, err := ioutil.ReadDir("s3_logs")
	if err != nil {
		log.Fatal(err)
	}
	var sb strings.Builder
	buf := bytes.NewBuffer(nil)
	for _, file := range fileNames {
		file, _ := os.Open(file.Name())
		buf.Reset()
		_, _ = io.Copy(buf, file)
		_ = file.Close()
		sb.Write(buf.Bytes())
		fmt.Println(sb.String())
	}
}
