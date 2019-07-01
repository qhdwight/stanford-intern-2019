import json

from django.shortcuts import render, redirect
from django.views.decorators.cache import cache_page

from . import query
from .forms import SelectTimeRangeForm
from .query import START_TIME, END_TIME


@cache_page(3600)
def dashboard(request, start_time=START_TIME, end_time=END_TIME):
    if request.method == 'POST':
        time_range_form = SelectTimeRangeForm(request.POST)
        if time_range_form.is_valid():
            return redirect('dashboard:dashboard_range',
                            start_time=time_range_form.cleaned_data['start_time'],
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

    # most_queried =
    QUICK = False
    most_queried = None if QUICK else query.get_most_queried_items_limited(20, start_time, end_time)
    graph_most_queried = None if QUICK else most_queried[:6]
    time_info = query.get_query_count_intervals(start_time, end_time)
    average_object_size = 0 if QUICK else int(query.get_average_object_size(start_time, end_time))
    total_request_count = 0 if QUICK else query.get_total_request_count(start_time, end_time)

    return render(request, 'dashboard.html', {
        'is_default': start_time is START_TIME and end_time is END_TIME,
        'start_time': start_time,
        'end_time': end_time,
        'time_range_form': time_range_form,
        'request_count': total_request_count,
        'average_object_size': average_object_size,
        'most_queried_table': most_queried,
        'most_queried_labels': json.dumps(
            [item.name for (item, _) in graph_most_queried]) if most_queried else None,
        'most_queried_data': json.dumps(
            [count for (_, count) in graph_most_queried]) if most_queried else None,
        # 'most_using_labels': json.dumps(list(graph_most_using.values_list('requester', flat=True))),
        # 'most_using_data': json.dumps(list(graph_most_using.values_list('count', flat=True))),
        'time_info_times': json.dumps([reading.time.isoformat() for reading in time_info]) if time_info else None,
        'time_info_counts': json.dumps([reading.count for reading in time_info] if time_info else None)
    })

@cache_page(3600)
def item_dashboard(request, item_name, start_time=START_TIME, end_time=END_TIME):
    if request.method == 'POST':
        time_range_form = SelectTimeRangeForm(request.POST)
        if time_range_form.is_valid():
            return redirect('dashboard:item_dashboard_range',
                            item_name=item_name,
                            start_time=time_range_form.cleaned_data['start_time'],
                            end_time=time_range_form.cleaned_data['end_time'])
    time_range_form = SelectTimeRangeForm()
    item = query.get_or_create_item(item_name)
    requesters = query.get_requesters_for_item(item, start_time, end_time)
    return render(request, 'item_dashboard.html', {
        'is_default': start_time is START_TIME and end_time is END_TIME,
        'start_time': start_time,
        'end_time': end_time,
        'time_range_form': time_range_form,
        'item': item,
        'request_breakdown': requesters
    })
