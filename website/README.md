# S3 Log Analysis Database
This repository features a PostgreSQL database that can be synced with the encode public log S3 bucket. It also combines data from the Encode website about experiments, file, etc to allow an easy interface between server logs and Encode objects. It uses the Django interface to be able to display information in a webserver, and also exposes the Django Python ORM for quick searches.

## How it Works
A sync Django command can be run, triggering a Go script which uses the AWS SDK to retrieve newer logs from the S3 bucket. Each log file contains multiple entries. Some are not useful, and are not included into the database. Only GET requests, partial and full, are entered into the database. The database ends up having millions of rows. Django allows a definition for database and handles creating tables and managing migrations. Schemas are defined in python and SQL commands are issued by Django to allow easy modifications and setup with the database.

Logs with invalid requests are also included in the database, which can be useful for analysis. The goal is to expose a python interface for quick searches, but also have the backend of Postgres to run more complicated searches.

## Details
### Database Authentication
The Postgres database has an admin. The password is in the `.env` file. Django automatically handles logging into the database. Check the jupyter files for information on how to setup Django in a regular python script. Commands can not be run without explicitly initializing the package.
### Running Django Commands
By default, logging into the EC2 instance logs into the `s3_usage` conda environment via the ubuntu `.bashrc`. This gives us access to all of the packages we need. When in the `website` directory, we can see there is a file named `manage.py`. This handles running all Django commands. I have created a special command named `sync` that can be found in `dashboard/management/sync.py`. Custom commands can be written following what is in that file. The format is `python manage.py <command name>`
### Database Migrations
Django handles migrating the database. When you change the `dashboard/models.py` file, you need to run the comand `python manage.py makemigrations` then `python manage.py migrate` to first make and then apply the migration. Migrations are actual python files that are run, they are stored in `dashboard/migrations` to keep history. Custom migrations CAN be written but if easy enough use Django commands.
### Raw Database Commands
Django supports executing raw commands. See the documentation. In addition to this, you can also run commands in the PSQL bash on the EC2 instance directly. You must enter `sudo su - postgres` to login to the Postgres user (It creates its own user on installation). Then, run `psql -d s3loganalysis` to open a shell in the database. `s3loganalysis` is the name of the database.
### Running the webserver
The webserver can be run with the command `python manage.py runserver`. It can be run in debug or regular mode. Debug mode is NOT SAFE and should not be used in production. It will basically dump all variables and information is there is a problem, which is a security issue. In production, turn debug to false in the `.env` file. This holds all configuration for the webserver and various other items. This is on the `.gitignore` because it has sensitive information. General, safe Django settings can be found in `activity_viewer/settings.py`.
### General Layout of webserver
The Django default templating language is not used. Instead, Jinja2 is used. The order of events from an HTTP request is: `urls.py` > `views.py` > Use `query.py` to get data > Render HTML file in `templates/` with "context", which binds python variables into the Jinja2 variables to be used in HTML files.

If using production (debug false), make sure to run the command `python manage.py collectstatic` first, as assets are compressed and cached. Set `CACHE_TIME` in `.env` as well to zero if testing so that pages will not be... cached.
### Website Usage and Extent of Ability
The website is not intended for complex use. Instead, see the Jupyter notebooks in 'dashboard/' for more complicated queries using the django ORM. Raw Postgres SQL statements can also be used. Check the Go script in `go/src/extract.go` for faster database access.
### Subtle Complexities of Project
The reason Go is used is because of its manual memory management and speed. It is compiled and takes advantage of multi-threaded goroutines to download data from S3 in parallel. In addition to this, it uses a growing buffer allocated once and extended if needed to save on heap allocation. In practice, this script was 2x faster and used 2x less CPU than the python script when initially transferring data into the database.

Originally, a Python script was used with `boto3` to access files and upload them. It was too slow. Then, I tried using `aws s3 sync` command to first clone to whole bucket, and they post-process insert into the database. This used too much disk space and is unwieldy. So, finally I settled on a Go script which takes advantage of sending multiple HTTP requests at once to the server and downloads data in chunks to process.

Batching is important because all of the data is too small to fit into RAM. Do not try to load all of the data at once, the process will be terminated by the OS for loading too much into memory.

Loading a small amount of data into `pandas` makes grouping or distinct selects faster since it is all in-memory. In general, distinct queries and counts are very slow in the Postgres database, as it requires a full database scan. This is the major reason why the homepage takes so long to load.

When migrating, make sure to run the `VACUUM FULL;` afterwards. It takes a long time, so aim for overnight. The indices are rebuilt, dead rows are reclaimed, and the speed improvement is very noticeable.

Run `python manage.py update_times` to allow for a time graph on the dashboard homepage. `python manage.py` allows the Bernstein experiment page to be properly rendered. It is also a good example of how to analyze across Log table and Item/Experiment tables.

To run the Go script by itself, the `GOPATH` environment variable must be set to the `go/` folder. To run, do `go run go/src/extract.go` command in terminal. This allows the current working directory to be set properly (run it from the website directory). If it need dependencies, run `go get ./...` in the `go/` directory. It uses packages from GitHub that must be downloaded before use.

To bind functions in HTML, use `activity_viewer/jinja_settings.py` to map them.
