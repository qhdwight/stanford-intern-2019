import os
from datetime import datetime, timedelta

import gc
from s3logparse import s3logparse
from tqdm import tqdm

from dashboard.models import Log

LOCAL_LOGS = 's3_logs'

BATCH_SIZE = 700


def get_model_from_log_line(log_file_name, log):
    # TODO compress somehow?
    return Log(
        key_name=log_file_name,
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
    """
    Looks in the folder specified above and goes through each text log file, adding to the database.
    Each log file may have multiple lines, which are treated as separate objects in the database.
    This skips log entries that are not GET or HEAD GET requests.
    """
    log_file_number = 0
    batched_models = []
    batch_time_spent_parsing = timedelta()
    last_batch_time = datetime.now()

    def save_batched():
        """
        Saves all of the log objects added to the list so far.
        This reduces stress on the database by actually doing disk writes every so many log files.
        """
        nonlocal last_batch_time, batched_models, batch_time_spent_parsing, log_file_number, log_file_name
        model_count = len(batched_models)
        database_insert_start = datetime.now()
        # This is where it is actually saved to the database
        Log.objects.bulk_create(batched_models)
        batched_models.clear()
        now = datetime.now()
        database_insert_start_time = datetime.now() - database_insert_start
        # Diagnostics to see how fast the program is running
        print(
            f'[{now}] On log #{log_file_number} with name {log_file_name}')
        print(f'Done with {model_count} objects and {log_file_number} logs')
        print(
            f'Database update took {database_insert_start_time} parsing took {batch_time_spent_parsing}')
        batch_time_spent_parsing = timedelta()
        batch_time_seconds = (now - last_batch_time).total_seconds()
        logs_per_second = model_count / batch_time_seconds
        print(f'Current rate of logs per second {logs_per_second}')
        last_batch_time = now
        # A lot of items are created on the heap during this process then never used again so collecting may help.
        gc.collect()

    already_seen = False
    # Looping through each actual log file on disk. They correspond to the time at which they were generated.
    for log_file_name in tqdm(os.listdir(LOCAL_LOGS)):
        # If we see a log file that has the file name already present in the database, skip it, as we have already
        # extracted every line from there.
        if already_seen:
            break
        log_file_number += 1
        parse_data_start_time = datetime.now()
        # Open log and create a model from each line if it has data we want
        with open(f'{LOCAL_LOGS}/{log_file_name}', 'r') as log_file:
            for log in s3logparse.parse_log_lines(log_file.readlines()):
                # Skip if we have already pulled this log file. Note this cancels out of the entire file.
                if Log.objects.filter(request_id=log.request_id).exists():
                    already_seen = True
                    break
                if log.operation != 'REST.GET.OBJECT' and log.operation != 'REST.HEAD.OBJECT':
                    continue
                # Converting S3 log parse object to django object.
                # TODO there are two conversions when one could do. Maybe the s3 log parse library should be ditched.
                model = get_model_from_log_line(log_file_name, log)
                batched_models.append(model)
        parse_delta = datetime.now() - parse_data_start_time
        # Add to running time spent parsing which rolls back every database update
        batch_time_spent_parsing += parse_delta
        # After a certain number of log entries commit them to the database in chunk
        if len(batched_models) >= BATCH_SIZE:
            save_batched()
    # If there are still models left at the end, but a batch was not triggered since it requires a certain amount,
    # make sure this smaller chunk is also saved to the database.
    if batched_models:
        save_batched()
