import glob
import os
import gc
from datetime import datetime, timedelta

from django.db import transaction
from s3logparse.s3logparse import parse_log_lines

from .models import Log

LOCAL_LOGS = 's3_logs'

BATCH_SIZE = 800

def get_model_from_log_line(key_name, log) -> Log:
    # TODO compress somehow?
    return Log(
        key_name=key_name,
        bucket=log.bucket,
        time=log.timestamp,
        ip_address=log.remote_ip,
        requester=log.requester,
        request_id=log.request_id,
        operation=log.operation,
        s3_key=log.s3_key,
        request_uri=log.request_uri,
        http_status=log.status_code,
        error_code=log.error_code,
        bytes_sent=log.bytes_sent,
        object_size=log.object_size,
        total_time=log.total_time,
        turn_around_time=log.turn_around_time,
        referrer=log.referrer,
        user_agent=log.user_agent,
        version_id=log.version_id
    )

def extract_from_local_into_database():
    log_file_number = 0
    models = []
    # Loop through all log files which have multiple log entries in them
    batch_time_spent_parsing = timedelta()
    last_batch_time = datetime.now()
    for file_name in os.listdir(LOCAL_LOGS):
        key_name = file_name
        log_file_number += 1
        # Skip if we have already pulled this log file
        if Log.objects.filter(key_name=key_name).exists():
            if log_file_number % 1000 == 0:
                print(f'[{datetime.now()}] Skipping through... at log #{log_file_number} with name {key_name}')
            continue
        start = datetime.now()
        # Open log and create a model from each line if it has data we want
        with open(LOCAL_LOGS + '/' + file_name, 'r') as log_file:
            for log in parse_log_lines(log_file.readlines()):
                if log.operation != 'REST.GET.OBJECT' and log.operation != 'REST.HEAD.OBJECT':
                    continue
                model = get_model_from_log_line(key_name, log)
                models.append(model)
        delta = datetime.now() - start
        # Add to running time spent parsing which rolls back every database update
        batch_time_spent_parsing += delta
        # After a certain number of log entries commit them to the database in chunk
        model_count = len(models)
        if model_count >= BATCH_SIZE:
            start = datetime.now()
            # Save all in one chunk
            Log.objects.bulk_create(models)
            models.clear()
            gc.collect()
            now = datetime.now()
            db_time = datetime.now() - start
            print(f'[{datetime.now()}] On log #{log_file_number} with name {key_name}')
            print(f'Done with {model_count} objets and {log_file_number} logs')
            print(f'Database update and GC collect took {db_time} parsing took {batch_time_spent_parsing}')
            batch_time_spent_parsing = timedelta()
            now = datetime.now()
            batch_time_seconds = (now - last_batch_time).total_seconds()
            if batch_time_seconds > 0:
                logs_per_second = model_count / batch_time_seconds
                print(f'Logs per second {logs_per_second}')
            else:
                print('zoooom')
            last_batch_time = now
