import json

from django.shortcuts import render, redirect
from django.views.decorators.cache import cache_page

from . import query
from .forms import SelectTimeRangeForm
from .query import START_TIME, END_TIME

CACHE_TIME = 0


def add_default_context(context, time_range_form, start_time, end_time):
    context.update({
        'is_default': start_time is START_TIME and end_time is END_TIME,
        'time_range_form': time_range_form,
        'start_time': start_time,
        'end_time': end_time
    })
    return context


@cache_page(CACHE_TIME)
def dashboard(request, start_time=START_TIME, end_time=END_TIME):
    if request.method == 'POST':
        time_range_form = SelectTimeRangeForm(request.POST)
        if time_range_form.is_valid():
            return redirect('dashboard:dashboard_range',
                            start_time=time_range_form.cleaned_data['start_time'],
                            end_time=time_range_form.cleaned_data['end_time'])
    time_range_form = SelectTimeRangeForm()
    most_queried = query.get_most_queried_items_limited(50, start_time, end_time)
    biggest_requesters = query.get_most_active_users_limited(100, start_time, end_time)
    graph_most_queried = most_queried[:6]
    time_info = query.get_query_count_intervals(start_time, end_time)
    total_requests, unique_requests, unique_ips, unique_files, unique_requesters, average_file_size = query.get_general_stats(
        start_time, end_time)
    return render(request, 'dashboard.html', add_default_context({
        'total_request_count': total_requests,
        'unique_request_count': unique_requests,
        'unique_ips': unique_ips,
        'unique_files': unique_files,
        'unique_requesters': unique_requesters,
        'average_file_size': average_file_size,
        'most_queried_table': most_queried,
        'biggest_users': biggest_requesters,
        'most_queried_labels': json.dumps(
            [item.name for (item, _) in graph_most_queried]) if most_queried else None,
        'most_queried_data': json.dumps(
            [count for (_, count) in graph_most_queried]) if most_queried else None,
        # 'most_using_labels': json.dumps(list(graph_most_using.values_list('requester', flat=True))),
        # 'most_using_data': json.dumps(list(graph_most_using.values_list('count', flat=True))),
        'time_info_times': json.dumps([reading.time.isoformat() for reading in time_info]) if time_info else None,
        'time_info_counts': json.dumps([reading.count for reading in time_info] if time_info else None)
    }, time_range_form, start_time, end_time))


@cache_page(CACHE_TIME)
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
    (request_breakdown, ip_breakdown) = query.get_requesters_for_item(item, start_time, end_time)
    return render(request, 'item_dashboard.html', add_default_context({
        'item': item,
        'request_breakdown': request_breakdown,
        'ip_breakdown': ip_breakdown
    }, time_range_form, start_time, end_time))


@cache_page(CACHE_TIME)
def requester_dashboard(request, requester, start_time=START_TIME, end_time=END_TIME):
    if request.method == 'POST':
        time_range_form = SelectTimeRangeForm(request.POST)
        if time_range_form.is_valid():
            return redirect('dashboard:requester_dashboard_range',
                            requester=requester,
                            start_time=time_range_form.cleaned_data['start_time'],
                            end_time=time_range_form.cleaned_data['end_time'])
    time_range_form = SelectTimeRangeForm()
    items = query.get_items_for_source(start_time, end_time, requester=requester)
    total_downloads, unique_downloads = query.get_stats_for_source(requester=requester)
    return render(request, 'user_dashboard.html', add_default_context({
        'unique_downloads': unique_downloads,
        'total_downloads': total_downloads,
        'requester': requester,
        'most_queried_table': items
    }, time_range_form, start_time, end_time))


@cache_page(CACHE_TIME)
def ip_address_dashboard(request, ip_address, start_time=START_TIME, end_time=END_TIME):
    if request.method == 'POST':
        time_range_form = SelectTimeRangeForm(request.POST)
        if time_range_form.is_valid():
            return redirect('dashboard:ip_address_dashboard_range',
                            ip_address=ip_address,
                            start_time=time_range_form.cleaned_data['start_time'],
                            end_time=time_range_form.cleaned_data['end_time'])
    time_range_form = SelectTimeRangeForm()
    items = query.get_items_for_source(start_time, end_time, ip_address=ip_address)
    total_downloads, unique_downloads = query.get_stats_for_source(start_time, end_time, ip_address=ip_address)
    return render(request, 'ip_address_dashboard.html', add_default_context({
        'unique_downloads': unique_downloads,
        'total_downloads': total_downloads,
        'ip_address': ip_address,
        'most_queried_table': items
    }, time_range_form, start_time, end_time))
