from django.db import models

ENCODE_URL_BASE = 'https://www.encodeproject.org'


def get_file_name(s3_key):
    return s3_key.split('/')[-1] if s3_key.count('/') > 1 else s3_key


def get_item_name(s3_key):
    name = get_file_name(s3_key)
    if '.' in name:
        name = name.split('.')[0]
    return name


def get_encode_url(name):
    return f'{ENCODE_URL_BASE}/{name}'


def get_encode_url_from_s3(s3_key):
    return get_encode_url(get_item_name(s3_key))


class Item(models.Model):
    s3_key = models.CharField(max_length=64, unique=True)
    experiment = models.CharField(max_length=64)
    assay_title = models.CharField(max_length=64)


class MostQueried(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    count = models.PositiveIntegerField()


class MostQueriedExperiment(models.Model):
    count = models.PositiveIntegerField()


class IntervalQueryCount(models.Model):
    time = models.DateTimeField()
    count = models.PositiveIntegerField()


class Log(models.Model):
    key_name = models.CharField(max_length=64, db_index=True)
    bucket = models.CharField(max_length=64, null=True)
    time = models.DateTimeField(null=True)
    ip_address = models.GenericIPAddressField(null=True)
    requester = models.CharField(max_length=512, null=True)
    request_id = models.CharField(max_length=64, unique=True)
    operation = models.CharField(max_length=64, null=True)
    s3_key = models.CharField(max_length=256, null=True)
    request_uri = models.CharField(max_length=4096, null=True)
    http_status = models.PositiveSmallIntegerField(null=True)
    error_code = models.CharField(max_length=64, null=True)
    bytes_sent = models.BigIntegerField(null=True)
    object_size = models.BigIntegerField(null=True)
    total_time = models.PositiveIntegerField(null=True)
    turn_around_time = models.PositiveIntegerField(null=True)
    referrer = models.URLField(null=True)
    user_agent = models.CharField(max_length=1024, null=True)
    version_id = models.CharField(max_length=1024, null=True)
    # host_id = models.CharField(max_length=1024)
    # UNAUTHENTICATED = 0
    # SIG_V2 = 1
    # SIG_V4 = 2
    # signature_version = models.PositiveSmallIntegerField(
    #     choices=[
    #         (UNAUTHENTICATED, None),
    #         (SIG_V2, 'SigV2'),
    #         (SIG_V4, 'SigV4')
    #     ]
    # )
    # cipher_suite = models.CharField(max_length=256)
    # AUTH_HEADER = 1
    # QUERY_STRING = 2
    # auth_type = models.PositiveSmallIntegerField(
    #     choices=[
    #         (UNAUTHENTICATED, None),
    #         (AUTH_HEADER, 'AuthHeader'),
    #         (QUERY_STRING, 'QueryString')
    #     ]
    # )
    # host_header=models.URLField()
    # NO_TLS = 0
    # TLS_V1 = 1
    # TLS_V1_1 = 2
    # TLS_V1_2 = 3
    # tls_version = models.PositiveSmallIntegerField(
    #     choices=[
    #         (NO_TLS, '-'),
    #         (TLS_V1, 'TLSv1'),
    #         (TLS_V1_1, 'TLSv1.1'),
    #         (TLS_V1_2, 'TLSv1.2')
    #     ]
    # )
