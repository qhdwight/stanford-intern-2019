import os
import glob

from .models import Log
from s3logparse.s3logparse import parse_log_lines

LOCAL_LOGS = 's3_logs'

LOG_EVERY_N = 1000

def save_model_from_raw_log(key_name, raw_log):
    for log in parse_log_lines(raw_log):
        model_log = Log(
            key_name=key_name,
            bucket_owner=log.bucket_owner,
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
        model_log.save()

def extract_from_local_into_database():
    log_file_number = 0
    for file_name in os.listdir(LOCAL_LOGS):
        key_name = file_name
        # Skip if we have already pulled this log file
        if Log.objects.filter(key_name=key_name).exists():
            continue
        log_file_number += 1
        with open(LOCAL_LOGS + '/' + file_name, 'r') as log_file:
            save_model_from_raw_log(key_name, log_file.readlines())
        if log_file_number % LOG_EVERY_N == 0:
            print(f'On log #{log_file_number} with name {key_name}')
