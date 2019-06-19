import glob
import os
import gc
from datetime import datetime, timedelta

from django.db import transaction
from s3logparse.s3logparse import parse_log_lines

from .models import Log

LOCAL_LOGS = 's3_logs'

BATCH_SIZE = 5000

def get_model_from_log_line(key_name, log) -> Log:
    model_log = Log(
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
    return model_log

def extract_from_local_into_database():
    log_file_number = 0
    models = []
    for file_name in os.listdir(LOCAL_LOGS):
        key_name = file_name
        log_file_number += 1
        # Skip if we have already pulled this log file
        # if Log.objects.filter(key_name=key_name).exists():
        #     if log_file_number % 1000 == 0:
        #         print(f'[{datetime.now()}] Skipping through... at log #{log_file_number} with name {key_name}')
        #     continue
        batch_time_spent_parsing = timedelta()
        start = datetime.now()
        with open(LOCAL_LOGS + '/' + file_name, 'r') as log_file:
            for log in parse_log_lines(log_file.readlines()):
                if log.operation != 'REST.GET.OBJECT' and log.operation != 'REST.HEAD.OBJECT':
                    continue
                model = get_model_from_log_line(key_name, log)
                models.append(model)
        delta = datetime.now() - start
        batch_time_spent_parsing += delta
        if len(models) >= BATCH_SIZE:
            start = datetime.now()
            with transaction.atomic():
                for model in models:
                    model.save()
            models.clear()
            gc.collect()
            db_time = datetime.now() - start
            print(f'[{datetime.now()}] On log #{log_file_number} with name {key_name}')
            print(f'Done with {BATCH_SIZE} objets and {log_file_number} logs')
            print(f'Database update and GC collect took {db_time} parsing took {batch_time_spent_parsing}')
            batch_time_spent_parsing = timedelta()
