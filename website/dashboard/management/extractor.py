import gc
import glob
import os
from datetime import datetime, timedelta
from itertools import chain

from django.db import transaction
from s3logparse import s3logparse

from dashboard.models import Log

LOCAL_LOGS = 's3_logs'

BATCH_SIZE = 700


def get_model_from_log_line(key_name, log):
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
    batched_models = []
    batch_time_spent_parsing = timedelta()
    last_batch_time = datetime.now()

    def save_batched():
        nonlocal last_batch_time, batched_models, batch_time_spent_parsing, log_file_number
        model_count = len(batched_models)
        database_insert_start = datetime.now()
        # Save all in one chunk
        Log.objects.bulk_create(batched_models)
        batched_models.clear()
        now = datetime.now()
        database_insert_start_time = datetime.now() - database_insert_start
        print(
            f'[{now}] On log #{log_file_number} with name {key_name}')
        print(f'Done with {model_count} objects and {log_file_number} logs')
        print(
            f'Database update took {database_insert_start_time} parsing took {batch_time_spent_parsing}')
        batch_time_spent_parsing = timedelta()
        batch_time_seconds = (now - last_batch_time).total_seconds()
        logs_per_second = model_count / batch_time_seconds
        print(f'Current rate of logs per second {logs_per_second}')
        last_batch_time = now
        gc.collect()

    # Loop through all log files which have multiple log entries in them
    already_seen = False
    for key_name in os.listdir(LOCAL_LOGS):
        if already_seen:
            break
        log_file_number += 1
        parse_data_start_time = datetime.now()
        # Open log and create a model from each line if it has data we want
        with open(f'{LOCAL_LOGS}/{key_name}', 'r') as log_file:
            for log in s3logparse.parse_log_lines(log_file.readlines()):
                # Skip if we have already pulled this log file
                if Log.objects.filter(request_id=log.request_id).exists():
                    already_seen = True
                    break
                if log.operation != 'REST.GET.OBJECT' and log.operation != 'REST.HEAD.OBJECT':
                    continue
                model = get_model_from_log_line(key_name, log)
                batched_models.append(model)
        parse_delta = datetime.now() - parse_data_start_time
        # Add to running time spent parsing which rolls back every database update
        batch_time_spent_parsing += parse_delta
        # After a certain number of log entries commit them to the database in chunk
        if len(batched_models) >= BATCH_SIZE:
            save_batched()
    if batched_models:
        save_batched()
