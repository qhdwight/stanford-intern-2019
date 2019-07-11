import sys
from datetime import timedelta, datetime

import pandas as pd
import requests
from django.db.models import Count, Avg
from django.utils import timezone

from dashboard.models import Log, Item, QueryCountAtTime, get_item_name, AnalysisLabItem, IpAddress

START_TIME = datetime(2019, 3, 1, tzinfo=timezone.get_current_timezone())
END_TIME = timezone.now()
INTERVAL_DELTA = timedelta(4)

ENCODE_URL_BASE = 'https://www.encodeproject.org'

GET_REQUESTS = Log.objects.filter(operation='REST.GET.OBJECT')
GET_JSON_HEADERS = {'accept': 'application/json'}

BERNSTEIN_EXPERIMENT_FILTER_KWARGS = {'item_name__in': AnalysisLabItem.objects.values_list('name', flat=True)}


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


def filter_from_time_range(start_time=START_TIME, end_time=END_TIME):
    is_default = start_time is START_TIME and end_time is END_TIME
    return GET_REQUESTS if is_default else GET_REQUESTS.filter(time__range=(start_time, end_time))


def get_most_queried_s3_keys(start_time=START_TIME, end_time=END_TIME, **kwargs):
    return (filter_from_time_range(start_time, end_time)
            .filter(**kwargs)
            .values('s3_key')
            .annotate(count=Count('ip_address', distinct=True))
            .values('s3_key', 'count')
            .order_by('-count'))


@time_this
def get_most_queried_items_limited(amount, start_time=START_TIME, end_time=END_TIME, page=0, **kwargs):
    items = [(get_or_create_item(get_item_name(queried['s3_key'])), queried['count']) for queried in
             take_page(get_most_queried_s3_keys(start_time, end_time, **kwargs), amount, page).iterator()]
    return items


def take_page(query_set, page_size, page):
    return query_set[page_size * page:page_size * (page + 1)]


@time_this
def get_most_active_users_limited(amount, start_time=START_TIME, end_time=END_TIME, page=0, **kwargs):
    return take_page(filter_from_time_range(start_time, end_time)
                     .filter(**kwargs)
                     .exclude(requester__contains='encoded-instance')
                     .values('ip_address')
                     .annotate(count=Count('ip_address'))
                     .values('requester', 'count', 'ip_address')
                     .order_by('-count'), amount, page)


def calculate_query_count_intervals(start_time=START_TIME, **kwargs):
    readings = []
    logs = GET_REQUESTS.filter(**kwargs)
    time = start_time
    # Iterate in chunks across database and sum up request count for evenly sized intervals
    while time < END_TIME:
        print(f'At time: {time}, end time: {END_TIME}')
        # Notice we filter data to left and right of the time
        count = logs.filter(time__range=(time - INTERVAL_DELTA / 2, time + INTERVAL_DELTA / 2)).count()
        time += INTERVAL_DELTA
        readings.append((time, count))
    return readings


@time_this
def get_query_count_intervals(start_time=START_TIME, end_time=END_TIME, data_set='all'):
    return QueryCountAtTime.objects.filter(data_set=data_set, time__range=(start_time, end_time))


@time_this
def get_general_stats(start_time=START_TIME, end_time=END_TIME, **kwargs):
    log_range = (filter_from_time_range(start_time, end_time)
                 .exclude(requester__contains='encoded-instance')
                 .filter(**kwargs))
    # Total requests, unique requests, unique ips, unique files
    key_and_ip = log_range.values('s3_key', 'ip_address')
    distinct_keys = key_and_ip.values('s3_key').distinct()
    return (log_range.count(),
            key_and_ip.distinct().count(),
            key_and_ip.values('ip_address').distinct().count(),
            distinct_keys.count(),
            log_range.values('requester').distinct().count(),
            int(distinct_keys.aggregate(average_size=Avg('object_size'))['average_size'] or 0))


@time_this
def get_requesters_for_item(item, start_time=START_TIME, end_time=END_TIME):
    keys = (filter_from_time_range(start_time, end_time)
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
    """

    :param start_time:
    :param end_time:
    :param kwargs:
    :return:
    """
    reqs = (filter_from_time_range(start_time, end_time)
            .filter(**kwargs))
    return (reqs
            .count(),
            reqs
            .values('s3_key')
            .distinct()
            .count())


@time_this
def get_items_for_source_limited(amount, start_time=START_TIME, end_time=END_TIME, page=0, **kwargs):
    """
    Get the most downloaded items for a given source by totals.
    The source should be a model fields that are passed to Django filter call, ex: requester or ip address
    :param amount: How many results to return. There are usually too many to return all
    :param start_time: When to start looking in the database for downloads
    :param end_time: When to stop looking in the database for downloads
    :param page: What page number. Default is zero,
    :param kwargs: Passed to Django filter of Log items
    :return: Database items that were most downloaded by this source
    """
    keys = take_page(filter_from_time_range(start_time, end_time)
                     .filter(**kwargs)
                     .values('s3_key')
                     # Group by S3 key and see how many total downloads there were
                     .annotate(count=Count('s3_key'))
                     .values('s3_key', 'count')
                     .order_by('-count'), amount, page)
    items = [(get_or_create_item(get_item_name(log['s3_key'])), log['count']) for log in keys.iterator()]
    return items


def get_or_create_ip_info(ip_address):
    if IpAddress.objects.filter(ip_address=ip_address):
        return IpAddress.objects.get(ip_address=ip_address)
    else:
        url = f'http://ip-api.com/json/{ip_address}'
        result = requests.get(url, headers=GET_JSON_HEADERS).json()
        return IpAddress.objects.create(
            ip_address=ip_address,
            isp=result['as'],
            country=result['country'],
            city=result['city'],
            latitude=result['lat'],
            longitude=result['lon']
        )


def get_or_create_item(item_name):
    """
    Items have more additional data attached to them, and it takes time to get it from encode servers, so
    they are only created when specifically requested. This is responsible for carrying out that if necessary.
    :param item_name: Name of the item. This is not the full S# key
    :return: The newly created or existing item in the database with additional information
    """
    if Item.objects.filter(name=item_name).exists():
        return Item.objects.get(name=item_name)
    else:
        # Item name is a truncated version of the S3 key
        first_log_with_item_name = Log.objects.filter(item_name=item_name).first()
        if not first_log_with_item_name:
            return None
        s3_key = first_log_with_item_name.s3_key
        # The manifest is a special file that does not have the experiment and assay data
        is_manifest = s3_key == 'encode_file_manifest.tsv'
        if is_manifest:
            experiment = None
            assay_title = None
        else:
            # Contact the encode server about this item to get additional information.
            # The response is JSON.
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


DATES_DF = None


def get_relative_access():
    global DATES_DF
    if not DATES_DF:
        DATES_DF = pd.read_csv('access_creation_dates.csv', parse_dates=['created', 'accessed'],
                               date_parser=pd.to_datetime)
    created_df = DATES_DF[['created']]
    accessed_by_year = created_df.groupby(created_df['created'].dt.year).size()
    return accessed_by_year
