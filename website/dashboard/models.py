from django.db import models


def get_item_name(s3_key):
    return s3_key.split('/')[-1] if s3_key.count('/') > 0 else s3_key


class IpAddress(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    isp = models.TextField(max_length=64)
    country = models.TextField(max_length=32)
    city = models.TextField(max_length=32)
    latitude = models.DecimalField(decimal_places=6, max_digits=9)
    longitude = models.DecimalField(decimal_places=6, max_digits=9)


class QueryCountAtTime(models.Model):
    """
    How many queries to the server were present in a interval centered around a time.
    This creates sort of a midpoint approximation of requests over time.
    """
    data_set = models.TextField(max_length=16)
    time = models.DateTimeField(db_index=True)
    count = models.PositiveIntegerField()


class Lab(models.Model):
    name = models.TextField(max_length=16, unique=True)


class Award(models.Model):
    name = models.TextField(max_length=16, null=True, unique=True)
    pi = models.TextField(max_length=16, null=True)
    project = models.TextField(max_length=8, null=True)
    rfa = models.TextField(max_length=8, null=True)
    status = models.TextField(max_length=8, null=True)


class Experiment(models.Model):
    name = models.TextField(max_length=32, unique=True)
    date_released = models.DateField(null=True)
    assay_title = models.TextField(max_length=8, null=True, db_index=True)
    assay_term_name = models.TextField(max_length=8, null=True)


class Item(models.Model):
    """
    An item that is represented as a file in the S3 server. They have a unique key.
    Information other than just the key name must be queried directly from the encode server.
    This takes time so it is done whenever necessary, not for all objects.
    """
    s3_key = models.TextField(max_length=64, unique=True)
    name = models.TextField(max_length=16, unique=True)
    # Gathered from the encode website via REST call when needed
    dataset = models.TextField(max_length=16, db_index=True)
    dataset_type = models.TextField(max_length=16, db_index=True)
    experiment = models.ForeignKey(Experiment, on_delete=models.PROTECT, null=True)
    # Total amount of times it has been accessed
    file_format = models.TextField(max_length=8, null=True)
    file_type = models.TextField(max_length=8, null=True)
    award = models.ForeignKey(Award, on_delete=models.PROTECT, null=True)
    lab = models.ForeignKey(Lab, on_delete=models.PROTECT, null=True)
    date_uploaded = models.DateField(null=True)


class Log(models.Model):
    item = models.ForeignKey(Item, null=True, on_delete=models.PROTECT)
    bucket = models.TextField(max_length=16, null=True)
    time = models.DateTimeField(null=True, db_index=True)
    ip_address = models.GenericIPAddressField(null=True, db_index=True)
    requester = models.TextField(max_length=64, null=True, db_index=True)
    request_id = models.TextField(max_length=16, db_index=True)
    operation = models.TextField(max_length=16, null=True)
    s3_key = models.TextField(max_length=64, null=True, db_index=True)
    request_uri = models.TextField(max_length=1024, null=True)
    http_status = models.PositiveSmallIntegerField(null=True, db_index=True)
    error_code = models.TextField(max_length=16, null=True, db_index=True)
    bytes_sent = models.BigIntegerField(null=True)
    object_size = models.BigIntegerField(null=True, db_index=True)
    total_time = models.PositiveIntegerField(null=True)
    turn_around_time = models.PositiveIntegerField(null=True)
    referrer = models.TextField(null=True)
    user_agent = models.TextField(max_length=128, null=True)
    version_id = models.TextField(max_length=128, null=True)
    # host_id = models.TextField(max_length=1024)
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
    # cipher_suite = models.TextField(max_length=256)
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


class AnalysisLabItem(models.Model):
    data_set = models.TextField(max_length=16)
    name = models.TextField(max_length=16, unique=True)
