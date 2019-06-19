import os.path
import time
from datetime import datetime, timedelta

import boto3
import pandas as pd
from decouple import config
from django.db import transaction
from s3logparse.s3logparse import LogLine, parse_log_lines

from dashboard.management.extractor import get_model_from_log_line
from dashboard.models import Log

BUCKET_NAME = 'encode-public-logs'


def crawl():
    # resource = boto3.resource(
    #     's3',
    #     aws_access_key_id=config('AWS_ACCESS_KEY'),
    #     aws_secret_access_key=config('AWS_SECRET_KEY')
    # )

    client = boto3.client(
        's3',
        aws_access_key_id=config('AWS_ACCESS_KEY'),
        aws_secret_access_key=config('AWS_SECRET_KEY')
    )

    # cloud_watch_client = boto3.client(
    #     'cloudwatch',
    #     region_name='us-west-2',
    #     aws_access_key_id=config('AWS_ACCESS_KEY'),
    #     aws_secret_access_key=config('AWS_SECRET_KEY')
    # )

    # response = cloud_watch_client.get_metric_statistics(
    #     Namespace='AWS/S3',
    #     MetricName='BucketSizeBytes',
    #     Dimensions=[
    #         {
    #             "Name": "BucketName",
    #             "Value": BUCKET_NAME
    #         },
    #         {
    #             "Name": "StorageType",
    #             "Value": "StandardStorage"
    #         }
    #     ],
    #     StartTime=datetime.now() - timedelta(days=1),
    #     EndTime=datetime.now(),
    #     Period=86400,
    #     Statistics=['Average']
    # )   
    # print(response['Datapoints'][-1]['Average'])

    paginator = client.get_paginator('list_objects_v2')
    pagination_config = {
        'MaxItems': 10,
        'PageSize': 1000
    }
    pages = paginator.paginate(
        Bucket=BUCKET_NAME, PaginationConfig=pagination_config)
    page_number = 0
    for page in pages:
        page_number += 1
        log_file_number = 0
        for content in page['Contents']:
            key_name = content['Key']
            # Skip if we have already pulled this log file
            if Log.objects.filter(key_name=key_name).exists():
                continue
            log_file_number += 1
            obj = client.get_object(Bucket=BUCKET_NAME, Key=key_name)
            log_lines = obj['Body'].read().decode('utf-8').splitlines(True)
            with transaction.atomic():
                for log in parse_log_lines(log_lines):
                    model = get_model_from_log_line(key_name, log)
                    model.save()
            if log_file_number % 100 == 0:
                print("Waiting...")
                time.sleep(2)
            print( f"Read log #{log_file_number} with size {content['Size']} bytes")

# bucket = res.Bucket(name='encode-public-logs')

# for file in bucket.objects.filter(Prefix='2019'):
#     print(file.key)

# TEST_LOG = '2019-02-09-00-30-22-D0F094C5D78D98D1'

# LOG_PATH = 's3_logs'

# if not os.path.exists(LOG_PATH):
#     os.mkdir(LOG_PATH)

# def get_local_or_download(name):
#     local_path = f'{LOG_PATH}/{name}'
#     if not os.path.exists(local_path):
#         bucket.download_file(name, local_path)
#     return open(local_path)


# rows = []
# column_headers = LogLine._fields

# for file in bucket.objects.filter(Prefix='2019').limit(5):
#     with get_local_or_download(file.key) as log:
#         for log_entry in parse_log_lines(log.readlines()):
#             rows.append(list(log_entry))

# data = pd.DataFrame(rows, columns=column_headers)
# print(data)
