import sys
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


def time_this(method):
    def timed(*args, **kw):
        start = datetime.now()
        result = method(*args, **kw)
        end = datetime.now()
        print(f'{method.__name__} took {end - start}')
        sys.stdout.flush()
        return result

    return timed


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
    # print(query.query)
    return (get_in_time_range(start_time, end_time)
            .values('s3_key')
            .annotate(count=Count('ip_address', distinct=True))
            .values('s3_key', 'count')
            .order_by('-count'))


@time_this
def get_most_queried_items_limited(amount, start_time=START_TIME, end_time=END_TIME):
    items = [(get_or_create_item(get_item_name(queried['s3_key'])), queried['count']) for queried in
             get_most_queried_s3_keys(start_time, end_time)[:amount].iterator()]
    return items


@time_this
def get_most_active_users_limited(amount, start_time=START_TIME, end_time=END_TIME):
    return (get_in_time_range(start_time, end_time)
                .exclude(requester__contains='encoded-instance')
                # .filter(requester__isnull=False)
                .values('ip_address')
                .annotate(count=Count('ip_address'))
                .values('requester', 'count', 'ip_address')
                .order_by('-count')[:amount])


@time_this
def get_query_count_intervals(start_time=START_TIME, end_time=END_TIME):
    return QueryCountAtTime.objects.filter(time__range=(start_time, end_time))


@time_this
def get_general_stats(start_time=START_TIME, end_time=END_TIME):
    log_range = get_in_time_range(start_time, end_time)
    # Total requests, unique requests, unique ips, unique files
    key_and_ip = log_range.values('s3_key', 'ip_address')
    distinct_keys = key_and_ip.values('s3_key').distinct()
    return (log_range.count(),
            key_and_ip.distinct().count(),
            key_and_ip.values('ip_address').distinct().count(),
            distinct_keys.count(),
            log_range.values('requester').distinct().count(),
            int(distinct_keys.aggregate(average_size=Avg('object_size'))['average_size']))


@time_this
def get_requesters_for_item(item, start_time=START_TIME, end_time=END_TIME):
    keys = (get_in_time_range(start_time, end_time)
            .filter(s3_key=item.s3_key))
    return (keys.values('requester')
            .annotate(count=Count('requester'))
            .values('requester', 'count')
            .exclude(count=0)
            .order_by('-count'),
            keys.values('ip_address')
            .annotate(count=Count('ip_address'))
            .values('ip_address', 'count')
            .order_by('-count'))


def get_stats_for_source(start_time=START_TIME, end_time=END_TIME, **kwargs):
    reqs = (get_in_time_range(start_time, end_time)
            .filter(**kwargs))
    return (reqs
            .count(),
            reqs
            .values('s3_key')
            .distinct()
            .count())


@time_this
def get_items_for_source(start_time=START_TIME, end_time=END_TIME, **kwargs):
    keys = (get_in_time_range(start_time, end_time)
            .filter(**kwargs)
            .values('s3_key')
            .annotate(count=Count('s3_key'))
            .values('s3_key', 'count')
            .order_by('-count'))[:20]
    items = [(get_or_create_item(get_item_name(log['s3_key'])), log['count']) for log in keys.iterator()]
    return items


def get_or_create_item(item_name):
    if Item.objects.filter(name=item_name).exists():
        return Item.objects.get(name=item_name)
    else:
        first_log_with_item_name = Log.objects.filter(s3_key__endswith=item_name).first()
        if not first_log_with_item_name:
            return None
        s3_key = first_log_with_item_name.s3_key
        is_manifest = s3_key == 'encode_file_manifest.tsv'
        if is_manifest:
            experiment = None
            assay_title = None
        else:
            url = f'{get_encode_url(s3_key.split("/")[3])}/?format=json'
            result = requests.get(url, headers=GET_JSON_HEADERS).json()
            experiment = result['dataset'].split('/')[2]
            experiment_url = f'{get_encode_url(experiment)}/?format=json'
            experiment_result = requests.get(experiment_url, headers=GET_JSON_HEADERS).json()
            assay_title = experiment_result['assay_title'] if 'assay_title' in experiment_result else None
        query_count = GET_REQUESTS.filter(s3_key=s3_key).count()
        print(
            f'Creating item {item_name}, query count: {query_count}, key {s3_key}, experiment {experiment}, and assay {assay_title}')
        return Item.objects.create(
            name=item_name,
            s3_key=s3_key,
            experiment=experiment,
            assay_title=assay_title,
            query_count=query_count
        )
