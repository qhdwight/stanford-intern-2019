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

	_ "github.com/lib/pq"
)

const (
	host     = "localhost"
	port     = 5432
	user     = "postgres"
	password = "eahutwwhajqmzfxyyasf"
	dbName   = "s3loganalysis"
)

func check(err error) {
	if err != nil {
		log.Panic(err)
	}
}

func main() {
	psqlLoginInfo := fmt.Sprintf(
		"host=%s port=%d user=%s password=%s dbname=%s sslmode=disable",
		host, port, user, password, dbName,
	)
	db, err := sql.Open("postgres", psqlLoginInfo); check(err)
	const logDir = "s3_logs"
	fileInfos, err := ioutil.ReadDir(logDir); check(err)
	var sb strings.Builder
	buf := bytes.NewBuffer(nil)
	csvFile, err := os.Create("logs.csv")
	for _, fileInfo := range fileInfos {
		sb.Reset()
		sb.WriteString(logDir)
		sb.WriteString("/")
		sb.WriteString(fileInfo.Name())
		file, err := os.Open(sb.String()); check(err)
		buf.Reset()
		_, err = io.Copy(buf, file); check(err)
		err = file.Close(); check(err)

		sb.Reset()
		sb.Write(buf.Bytes())

	}
	err = csvFile.Close(); check(err)
	err = db.Close(); check(err)
}
