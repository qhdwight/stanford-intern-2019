import json

from django.db.models import Avg, Count
from django.shortcuts import render, get_object_or_404

from .models import Log, Item, MostQueried, IntervalQueryCount, get_file_name


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

    graph_most_queried = MostQueried.objects.all()[:6]
    time_info = IntervalQueryCount.objects.all()
    average_object_size = Log.objects.values('s3_key').distinct().aggregate(average_size=Avg('object_size'))

    return render(request, 'dashboard.html', {
        'request_count': Log.objects.count(),
        'average_object_size': int(average_object_size['average_size']),
        'most_queried_table': MostQueried.objects.all()[:50],
        'most_queried_labels': json.dumps(
            [get_file_name(most_queried.item.s3_key) for most_queried in graph_most_queried]),
        'most_queried_data': json.dumps(list(graph_most_queried.values_list('count', flat=True))),
        # 'most_using_labels': json.dumps(list(graph_most_using.values_list('requester', flat=True))),
        # 'most_using_data': json.dumps(list(graph_most_using.values_list('count', flat=True))),
        'time_info_times': json.dumps([time.time.isoformat() for time in time_info]),
        'time_info_counts': json.dumps(list(time_info.values_list('count', flat=True)))
    })


def item_dashboard(request, item_name):
    item = get_object_or_404(Item, s3_key__endswith=item_name)
    requesters = Log.objects \
        .filter(operation='REST.GET.OBJECT', s3_key=item.s3_key) \
        .values('requester', 's3_key') \
        .annotate(count=Count('requester')) \
        .exclude(count=0) \
        .order_by('-count')
    return render(request, 'item_dashboard.html', {
        'item_name': item_name,
        'request_breakdown_labels': list(requesters.values_list('requester', flat=True)),
        'request_breakdown_data': list(requesters.values_list('count', flat=True))
    })
