from datetime import timedelta, datetime

import requests
from django.db import transaction
from django.db.models import Count, Avg
from django.utils import timezone

from dashboard.models import Log, Item, QueryCountAtTime, get_item_name

START_TIME = datetime(2019, 3, 1, tzinfo=timezone.get_current_timezone())
END_TIME = timezone.now()
INTERVAL_DELTA = timedelta(4)

ENCODE_URL_BASE = 'https://www.encodeproject.org'

GET_REQUESTS = Log.objects.filter(operation='REST.GET.OBJECT')
GET_JSON_HEADERS = {'accept': 'application/json'}


def get_header(s3_key):
    name = get_item_name(s3_key)
    if '.' in name:
        name = name.split('.')[0]
    return name


def get_encode_url(name):
    return f'{ENCODE_URL_BASE}/{name}'


def get_encode_url_from_s3(s3_key):
    return get_encode_url(get_item_name(s3_key))


def get_in_time_range(start_time=START_TIME, end_time=END_TIME):
    return GET_REQUESTS.filter(time__range=(start_time, end_time))


def get_most_queried_s3_keys(start_time=START_TIME, end_time=END_TIME):
    # See which objects are queried the most
    return get_in_time_range(start_time, end_time) \
        .values('s3_key', 'ip_address') \
        .distinct() \
        .annotate(count=Count('s3_key')) \
        .order_by('-count')


def get_most_queried_items_limited(amount, start_time=START_TIME, end_time=END_TIME):
    items = []
    with transaction.atomic():
        for queried in get_most_queried_s3_keys(start_time, end_time)[:amount]:
            items.append(get_or_create_item(get_item_name(queried['s3_key'])))
    return items


def get_query_count_intervals(start_time=START_TIME, end_time=END_TIME):
    return QueryCountAtTime.objects.filter(time__range=(start_time, end_time))
    # readings = []
    # time = start_time
    # while time < end_time:
    #     count = GET_REQUESTS.filter(time__range=(time - interval_delta / 2, time + interval_delta / 2)).count()
    #     time += interval_delta
    #     readings.append((time, count))
    # return readings


def get_average_object_size(start_time=START_TIME, end_time=END_TIME):
    return get_in_time_range(start_time, end_time) \
        .values('s3_key') \
        .distinct() \
        .aggregate(average_size=Avg('object_size'))


def get_total_request_count(start_time=START_TIME, end_time=END_TIME):
    return get_in_time_range(start_time, end_time).count()


def get_requesters_for_item(item_name):
    item = get_or_create_item(item_name)
    return GET_REQUESTS \
        .filter(s3_key=item.s3_key) \
        .values('requester', 's3_key') \
        .annotate(count=Count('requester')) \
        .exclude(count=0) \
        .order_by('-count')


def get_or_create_item(item_name):
    if Item.objects.filter(name=item_name).exists():
        return Item.objects.get(name=item_name)
    else:
        first_log_with_item_name = Log.objects.filter(s3_key__endswith=item_name).first()
        if not first_log_with_item_name:
            return None
        s3_key = first_log_with_item_name.s3_key
        url = f'{get_encode_url(get_header(item_name))}/?format=json'
        result = requests.get(url, headers=GET_JSON_HEADERS).json()
        experiment = result['dataset'].split('/')[2]
        experiment_url = f'{get_encode_url(experiment)}/?format=json'
        experiment_result = requests.get(experiment_url, headers=GET_JSON_HEADERS).json()
        assay_title = experiment_result['assay_title']
        query_count = GET_REQUESTS.filter(s3_key=s3_key).count()
        print(f'Creating item {item_name}, query count: {query_count}, key {s3_key}, experiment {experiment}, and assay {assay_title}')
        return Item.objects.create(
            name=item_name,
            s3_key=s3_key,
            experiment=experiment,
            assay_title=assay_title,
            query_count=query_count
        )
