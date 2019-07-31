# S3 Log Analysis Database
This repository features a Postgres database that can be synced with the encode public log S3 bucket. It also combines data from the Encode website about experiments, files, etc to allow an easy interface between server logs and Encode objects. It uses the Django interface to be able to display information in a web server, and also exposes the Django Python ORM for quick searches.

## How it Works
A sync Django command can be run, triggering a Go script that uses the AWS SDK to retrieve newer logs from the S3 bucket. Each log file contains multiple entries. Some are not useful and are not included in the database. Only GET requests, partial and full, are entered into the database. The database ends up having millions of rows. Django allows a definition for database and handles creating tables and managing migrations. Schemas are defined in python and SQL commands are issued by Django to allow easy modifications and setup with the database.

Logs with invalid requests are also included in the database, which can be useful for analysis. The goal is to expose a python interface for quick searches, but also have the back-end of Postgres to run more complicated searches.

The EC2 instance can be stopped and restarted without a problem - but ideally make sure that all active queries are stopped before stopping.

## Jupyter Notebook Examples
Access the IP address of the EC2 instance with port 8888 in the browser to access the Jupyter notebooks. Go to the `dashboard` folder and there are examples of how to use the Django ORM and sometimes pandas to analyze data. **IMPORTANT**: If a token is required see the instructions under subtleties.

## Python Shell
To access the ORM and generate queries in python, run the following command `python manage.py shell` in the `website/` directory. This handles setting up Django for you. The result with be an interactive python shell where you can run any command or [query](https://docs.djangoproject.com/en/2.2/topics/db/queries/) you want. See the examples in the Jupyter notebooks for more information.

Example:

```
(s3_usage) ubuntu@ip-172-31-24-1:~/stanford-intern-2019/website$ python manage.py shell
Python 3.7.3 (default, Mar 27 2019, 22:11:17) 
Type 'copyright', 'credits' or 'license' for more information
IPython 7.6.1 -- An enhanced Interactive Python. Type '?' for help.

In [1]: from dashboard.models import Log                                                                                                                    

In [2]: Log.objects.count()                                                                                                                                 
Out[2]: 33991950
```

## Interactive Website
There is a website that allows you to explore the data in a basic manner. To access, run `python manage.py runserver <ip>:8000` where IP is the private one of the EC2 instance, which can be found in the dashboard. Then, it can be accessed at the public IP of the EC2 instance in your brower.  The website is slow initially, so give a couple of minutes for the homepage or other queries. **IMPORTANT**: Add your IP to the security group in the EC2 dashboard to be able to access the server. See subtleties for more information.


## Details
### Database Authentication
The Postgres database has an admin. The password is in the `.env` file. Django automatically handles logging into the database. Check the Jupyter files for information on how to set up Django in a regular python script. Commands can not be run without explicitly initializing the package.
### Running Django Commands
By default, logging into the EC2 instance logs into the `s3_usage` python conda environment via the `.bashrc`. This gives us access to all of the packages we need. When in the `website` directory, we can see there is a file named `manage.py`. This handles running all Django commands. I have created a special command named `sync` that can be found in `dashboard/management/sync.py`. Custom commands can be written following what is in that file. The format is `python manage.py <command name>`. So, to run the sync command, from your SSH terminal enter `python manage.py sync`.
### Database Migrations
Django handles [migrating](https://docs.djangoproject.com/en/2.2/topics/migrations/) the database. When you change the `dashboard/models.py` file, you need to run the command `python manage.py makemigrations` then `python manage.py migrate` to first make and then apply the migration. Django will automatically look at what has changed in the schema represented in the models python file. Migrations are actual python files that are run, they are stored in `dashboard/migrations` to keep history. Custom migrations CAN be written but if easy enough use Django commands.
### Raw Database Commands
Django supports executing raw commands. See the [documentation](https://docs.djangoproject.com/en/2.2/topics/db/sql/). In addition to this, you can also run commands in the PSQL bash on the EC2 instance directly. You must enter `sudo su - postgres` to login to the Postgres user (It creates one on installation). Then, run `psql -d s3loganalysis` to open a shell in the database. `s3loganalysis` is the name of the database.
### Running the Web Server
The web server can be run with the command `python manage.py runserver <ip>:<port>`. It can be run in debug or regular mode. Debug mode is NOT SAFE and should not be used in production. It will dump all variables and information is there is a problem, which is a security issue. In production, set the debug variable to false in the `.env` file. This holds all configuration for the webserver and various other items. This is on the `.gitignore` because it has sensitive information. These values are loaded into `activity_viewer/settings.py` to combine with non-sensitive settings and define how Django runs the server. The IP should be the private one of the EC2 instance, then you can access it via its public IP on your computer. Make sure to also update the security group so that you can access it from your specific computer, since right now it is locked down (since running in debug mode).
### General Layout of Web Server
The Django default templating language is not used. Instead, [Jinja2](https://jinja.palletsprojects.com/en/2.10.x/) is used. The order of events from an HTTP request is: `urls.py` > `views.py` > Use `query.py` to get data > Render HTML file in `templates/` with "context", which binds python variables into the Jinja2 variables to be used in HTML files.
### Running in Production/Debug Mode
If using production (debug false), make sure to run the command `python manage.py collectstatic` first, as assets are compressed and cached. Set `CACHE_TIME` in `.env` as well to zero if testing so that pages will not be... cached. However, in production you want this since many queries take a long time to run.
### Website Usage and Extent of Ability
The website is not intended for complex use. Instead, see the Jupyter notebooks in 'dashboard/' for more complicated queries using the django ORM. Raw Postgres SQL statements can also be used. Check the Go script in `go/src/extract.go` for faster database access.
### Subtle Complexities of Project
The reason Go is used is because of its manual memory management and speed. It is compiled and takes advantage of multi-threaded goroutines to download data from S3 in parallel. In addition to this, it uses a growing buffer that extends if needed to save on heap allocation. In practice, this script was 2x faster and used 2x less CPU than the python script when initially transferring data into the database.

Originally, a Python script was used with `boto3` to access files and upload them. It was too slow. Then, I tried using `aws s3 sync` command to first clone the whole bucket, and they post-process insert into the database. This used too much disk space and is unwieldy. So, finally, I settled on a Go script which takes advantage of sending multiple HTTP requests at once to the server and downloads data in chunks to process. It is a similar process to what the CLI does, except it is reading the contents into a memory buffer, not individuals local files. It is better to run any big downloading command on the EC2 instance to save money, since it costs less if you are in the AWS environment.

Batching is important because all of the data is too small to fit into RAM. Do not try to load all of the data at once, the process will be terminated by the OS for loading too much into memory.

Loading a small amount of data into `pandas` makes grouping or distinct selects faster since it is all in-memory. In general, distinct queries and counts are very slow in the Postgres database, as it requires a full database scan. This is the major reason why the homepage takes so long to load.

When migrating, make sure to run the Postgres `VACUUM (FULL, ANALYZE, VERBOSE);` command afterward. It takes a long time, so aim for overnight. The indices are rebuilt, dead rows are reclaimed, and the speed improvement is very noticeable.

Run `python manage.py update_times` to allow for a time graph on the dashboard homepage. `python manage.py` allows the Bernstein experiment page to be properly rendered. It is also a good example of how to analyze across Log table and Item/Experiment tables.

~~To run the Go script by itself, the `GOPATH` environment variable must be set to the `go/` folder. To run, do `go run go/src/extract.go` command in terminal. This allows the current working directory to be set properly (run it from the website directory). If it needs dependencies, run `go get ./...` in the `go/` directory. It uses packages from GitHub that must be downloaded before use.~~

I set the go script to use [go modules](https://github.com/golang/go/wiki/Modules) now to avoid setting the `GOPATH` environment variables. Make sure you are in the `website` directory (go needs this as workign directory to properly access certain files, it reads from `.env` to get password for database). To extract, run `go run go/src/extract.go` and it should automatically download and install all dependencies required.

To bind functions in HTML, use `activity_viewer/jinja_settings.py` to map them.

Try to use Django ORM to filter data before putting into `pandas` as there is a memory concern. It also takes a long time to load more than a million rows into a dataframe. In addition to this, use `values_list` instead of `values` and define columns manually for dataframe as it saves memory. The ORM is faster at filter operations but slower with distinct and grouping. Consider using [dask](https://dask.org/) in the future?

I used [this](https://pgtune.leopard.in.ua/#/) to try and tune the performance of the system. I used the alter system commands in the psql shell instead of  `postgresql.conf`

When running long commands, consider running it inside of a `tmux` instance. If the pipe breaks with SSH your progress will not be lost. `tmux new` to start, `Ctrl B-D` to detach, and `tmux a` to resume. `tmux ls` to view active.

#### Jupter Notebook

The Jupyter notebooks are a run by a `systemctl` service named `s3notebooks`. It should be started every time the instance reboots. To manually edit it, run the following:
```
sudo vim /etc/systemd/system/s3notebooks.service
sudo systemctl daemon-reload && sudo systemctl restart s3notebooks
```

First edits the service definition and the second reloads it.

You may need a token. If so, run `sudo systemctl stop s3notebooks`, run `StartNotebook.sh` in `website/dashboard/` to get the token. You should only need to do this once.

By default it is bound to the private IP of the EC2 instance. I assigned an elastic IP in the dashboard so the IP should stay the same.

## Useful Commands

|Command|Use|
|---|---|
|`jupyter notebook --port 8888 --ip 172.31.24.1 --no-browser`|Run the Jupyter server manually. Run in `website/`|
|`go run go/src/extract.go`|Extract manually with Go|
|`python manage.py migrate`|Create migrations from `models.py`|
|`python manage.py sync`|Update items and logs. Add `--skip` option to skip updating items|
|`python manage.py update_times`|Update the times that make the graph on the homepage|
|`python manage.py runserver 172.31.24.1:8000`|Run the Django server|
|`python manage.py shell`|Get into a python shell with Django initialized|
|`watch iostat -d`|View the IOPs of the database disk|
|`tmux new` and `tmux ls` and `tmux a`|tmux is a handy tool that allows commands to be run in sub-shells that can be detached and left to run|
