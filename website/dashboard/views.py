import json

from django.shortcuts import render, redirect

from . import query
from .forms import SelectTimeRangeForm
from .query import START_TIME, END_TIME


def dashboard(request, start_time=START_TIME, end_time=END_TIME):
    if request.method == 'POST':
        time_range_form = SelectTimeRangeForm(request.POST)
        if time_range_form.is_valid():
            return redirect('dashboard:dashboard_range', start_time=time_range_form.cleaned_data['start_time'],
                            end_time=time_range_form.cleaned_data['end_time'])
    time_range_form = SelectTimeRangeForm()

    # most_using = get_requests \
    #     .values('requester') \
    #     .filter(requester__contains='user/') \
    #     .exclude(requester__contains='user/pds-test-user') \
    #     .exclude(requester__contains='user/admin2') \
    #     .exclude(requester__contains='user/test1') \
    #     .annotate(total=Count('requester')) \
    #     .order_by('-total')
    # graph_most_using = most_using[:10]`z
    # print(graph_most_using)

    most_queried = query.get_most_queried_items_limited(10, start_time, end_time)
    graph_most_queried = most_queried[:6]
    time_info = query.get_query_count_intervals(start_time, end_time)
    average_object_size = query.get_average_object_size(start_time, end_time)['average_size']

    return render(request, 'dashboard.html', {
        'time_range_form': time_range_form,
        'request_count': query.get_total_request_count(start_time, end_time),
        'average_object_size': int(average_object_size) if average_object_size else 0,
        'most_queried_table': most_queried,
        'most_queried_labels': json.dumps([most_queried.name for most_queried in graph_most_queried]),
        'most_queried_data': json.dumps([most_queried.query_count for most_queried in graph_most_queried]),
        # 'most_using_labels': json.dumps(list(graph_most_using.values_list('requester', flat=True))),
        # 'most_using_data': json.dumps(list(graph_most_using.values_list('count', flat=True))),
        'time_info_times': json.dumps([reading.time.isoformat() for reading in time_info]),
        'time_info_counts': json.dumps([reading.count for reading in time_info])
    })


def item_dashboard(request, item_name):
    requesters = query.get_requesters_for_item(item_name)
    if not requesters:
        return redirect('dashboard:dashboard')
    return render(request, 'item_dashboard.html', {
        'item_name': item_name,
        'request_breakdown_labels': list(requesters.values_list('requester', flat=True)),
        'request_breakdown_data': list(requesters.values_list('count', flat=True))
    })
