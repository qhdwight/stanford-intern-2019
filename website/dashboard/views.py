from django.db.models import Count
from django.shortcuts import render

from .models import Log
import json


def parse_key(s3_key):
    if s3_key.count('/') > 1:
        return s3_key.split('/')[-1]
    return s3_key


def dashboard(request):
    request_count = Log.objects.count()
    most_queried_s3_keys = Log.objects.values('s3_key').annotate(
        total=Count('s3_key')).order_by('-total')
    graph_most_queried = most_queried_s3_keys[:6]
    table_most_queried = most_queried_s3_keys[:50]
    most_queried_labels = json.dumps(
        [parse_key(s3_key) for s3_key in graph_most_queried.values_list('s3_key', flat=True)])
    most_queried_data = json.dumps(list(graph_most_queried.values_list('total', flat=True)))
    # most_using = Log.objects.values('requester').annotate(total=Count('requester')).order_by('-total')
    # graph_most_using = most_using[:6]
    # most_using_labels = json.dumps(list(graph_most_using.values_list('requester', flat=True)))
    # most_using_data = json.dumps(list(graph_most_using.values_list('total', flat=True)))
    return render(request, 'dashboard.html', {
        'request_count': request_count,
        'most_queried': table_most_queried,
        'most_queried_labels': most_queried_labels,
        'most_queried_data': most_queried_data,
        # 'most_using_labels': most_using_labels,
        # 'most_using_data': most_using_data
    })
