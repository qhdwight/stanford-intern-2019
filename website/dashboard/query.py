from datetime import timedelta, datetime

from django.db.models import Count, Avg
from django.shortcuts import get_object_or_404
from django.utils import timezone

from dashboard.models import Log, Item

START_TIME = datetime(2019, 3, 1, tzinfo=timezone.get_current_timezone())
END_TIME = timezone.now()

GET_REQUESTS = Log.objects.filter(operation='REST.GET.OBJECT')


def get_in_time_range(start_time=START_TIME, end_time=END_TIME):
    return GET_REQUESTS.filter(time__range=(start_time, end_time))


def get_most_queried_s3_keys(start_time=START_TIME, end_time=END_TIME):
    # See which objects are queried the most
    return get_in_time_range(start_time, end_time) \
        .values('s3_key', 'ip_address') \
        .distinct() \
        .annotate(count=Count('s3_key')) \
        .order_by('-count')


def get_query_count_intervals(start_time=START_TIME, end_time=END_TIME, interval_delta=timedelta(4)):
    readings = []
    time = start_time
    while time < end_time:
        count = GET_REQUESTS.filter(time__range=(time - interval_delta / 2, time + interval_delta / 2)).count()
        time += interval_delta
        readings.append((time, count))
    return readings


def get_average_object_size(start_time=START_TIME, end_time=END_TIME):
    return get_in_time_range(start_time, end_time) \
        .values('s3_key') \
        .distinct() \
        .aggregate(average_size=Avg('object_size'))


def get_total_request_count(start_time=START_TIME, end_time=END_TIME):
    return get_in_time_range(start_time, end_time).count()


def get_requesters_for_item(item_name):
    item = get_object_or_404(Item, name=item_name)
    return GET_REQUESTS \
        .filter(s3_key=item.s3_key) \
        .values('requester', 's3_key') \
        .annotate(count=Count('requester')) \
        .exclude(count=0) \
        .order_by('-count')
