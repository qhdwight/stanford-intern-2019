import json

from django.shortcuts import render

from .query import get_most_queried_s3_keys, get_query_count_intervals, get_average_object_size, \
    get_total_request_count, get_requesters_for_item

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


def dashboard(request):
    # get_requests = Log.objects.filter(operation='REST.GET.OBJECT')
    #
    # most_queried_s3_keys = get_requests \
    #     .values('s3_key', 'ip_address') \
    #     .distinct() \
    #     .annotate(total=Count('s3_key')) \
    #     .order_by('-total')
    # table_most_queried = most_queried_s3_keys[:50]
    # graph_most_queried = most_queried_s3_keys[:6]
    #
    # most_using = get_requests \
    #     .values('requester') \
    #     .filter(requester__contains='user/') \
    #     .exclude(requester__contains='user/pds-test-user') \
    #     .exclude(requester__contains='user/admin2') \
    #     .exclude(requester__contains='user/test1') \
    #     .annotate(total=Count('requester')) \
    #     .order_by('-total')
    # graph_most_using = most_using[:10]
    # print(graph_most_using)

    most_queried = get_most_queried_s3_keys()
    graph_most_queried = most_queried[:6]
    time_info = get_query_count_intervals()

    return render(request, 'dashboard.html', {
        'request_count': get_total_request_count(),
        'average_object_size': int(get_average_object_size()['average_size']),
        'most_queried_table': most_queried[:50],
        'most_queried_labels': json.dumps(
            [get_file_name(most_queried.item.s3_key) for most_queried in graph_most_queried]),
        'most_queried_data': json.dumps(list(graph_most_queried.values_list('count', flat=True))),
        # 'most_using_labels': json.dumps(list(graph_most_using.values_list('requester', flat=True))),
        # 'most_using_data': json.dumps(list(graph_most_using.values_list('count', flat=True))),
        'time_info_times': json.dumps([time.time.isoformat() for time in time_info]),
        'time_info_counts': json.dumps(list(time_info.values_list('count', flat=True)))
    })


def item_dashboard(request, item_name):
    requesters = get_requesters_for_item(item_name)
    return render(request, 'item_dashboard.html', {
        'item_name': item_name,
        'request_breakdown_labels': list(requesters.values_list('requester', flat=True)),
        'request_breakdown_data': list(requesters.values_list('count', flat=True))
    })
