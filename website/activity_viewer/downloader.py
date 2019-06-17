import os.path

import boto3
import pandas as pd
from decouple import config
from s3logparse.s3logparse import parse_log_lines, LogLine

s3 = boto3.resource(
    's3',
    aws_access_key_id=config('ACCESS_KEY'),
    aws_secret_access_key=config('SECRET_KEY')
)

bucket = s3.Bucket(name='encode-public-logs')

# for file in bucket.objects.filter(Prefix='2019'):
#     print(file.key)

TEST_LOG = '2019-02-09-00-30-22-D0F094C5D78D98D1'

LOG_PATH = 's3_logs'

if not os.path.exists(LOG_PATH):
    os.mkdir(LOG_PATH)

def get_local_or_download(name):
    local_path = f'{LOG_PATH}/{name}'
    if not os.path.exists(local_path):
        bucket.download_file(name, local_path)
    return open(local_path)


rows = []
column_headers = LogLine._fields

for file in bucket.objects.filter(Prefix='2019').limit(5):
    with get_local_or_download(file.key) as log:
        for log_entry in parse_log_lines(log.readlines()):
            rows.append(list(log_entry))

data = pd.DataFrame(rows, columns=column_headers)
print(data)
