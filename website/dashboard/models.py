from django.db import models


def get_item_name(s3_key):
    return s3_key.split('/')[-1] if s3_key.count('/') > 0 else s3_key


class QueryCountAtTime(models.Model):
    """
    How many queries to the server were present in a interval centered around a time.
    This creates sort of a midpoint approximation of requests over time.
    """
    time = models.DateTimeField(unique=True)
    count = models.PositiveIntegerField()


class Item(models.Model):
    """
    An item that is represented as a file in the S3 server. They have a unique key.
    Information other than just the key name must be queried directly from the encode server.
    This takes time so it is done whenever necessary, not for all objects.
    """
    s3_key = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=64, unique=True)
    # Gathered from the encode website via REST call when needed
    experiment = models.CharField(max_length=64, null=True)
    assay_title = models.CharField(max_length=64, null=True)
    # Total amount of times it has been accessed
    query_count = models.PositiveIntegerField()


class Log(models.Model):
    item_name = models.CharField(max_length=16, db_index=True, null=True)
    key_name = models.CharField(max_length=32)
    bucket = models.CharField(max_length=16, null=True)
    time = models.DateTimeField(null=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, db_index=True)
    requester = models.CharField(max_length=64, null=True, db_index=True)
    request_id = models.CharField(max_length=16, unique=True)
    operation = models.CharField(max_length=16, null=True)
    s3_key = models.CharField(max_length=64, null=True, db_index=True)
    request_uri = models.CharField(max_length=1024, null=True)
    http_status = models.PositiveSmallIntegerField(null=True)
    error_code = models.CharField(max_length=16, null=True)
    bytes_sent = models.BigIntegerField(null=True)
    object_size = models.BigIntegerField(null=True, db_index=True)
    total_time = models.PositiveIntegerField(null=True)
    turn_around_time = models.PositiveIntegerField(null=True)
    referrer = models.URLField(null=True)
    user_agent = models.CharField(max_length=128, null=True)
    version_id = models.CharField(max_length=128, null=True)
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


class ExperimentItem(models.Model):
    name = models.CharField(max_length=16, unique=True)


class UniqueExperimentItemAccess(models.Model):
    log = models.ForeignKey(Log, on_delete=models.CASCADE)
