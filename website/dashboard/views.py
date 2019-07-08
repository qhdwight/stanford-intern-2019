import json

from django.shortcuts import render, redirect
from django.views.decorators.cache import cache_page

from . import query
from .forms import SelectTimeRangeForm
from .query import START_TIME, END_TIME

from django.conf import settings


def add_default_context(context, time_range_form, start_time, end_time):
    context.update({
        'is_default': start_time is START_TIME and end_time is END_TIME,
        'time_range_form': time_range_form,
        'start_time': start_time,
        'end_time': end_time
    })
    return context


def add_table_context(context, start_time, end_time, page, page_size):
    context = add_default_context(context, None, start_time, end_time)
    context.update({
        'table_page': page,
        'table_page_size': page_size
    })
    return context


@cache_page(settings.CACHE_TIME)
def dashboard(request, start_time=START_TIME, end_time=END_TIME):
    if request.method == 'POST':
        time_range_form = SelectTimeRangeForm(request.POST)
        if time_range_form.is_valid():
            return redirect(request.resolver_match.view_name,
                            start_time=time_range_form.cleaned_data['start_time'],
                            end_time=time_range_form.cleaned_data['end_time'])
    else:
        time_range_form = SelectTimeRangeForm()
    graph_most_queried = query.get_most_queried_items_limited(6, start_time, end_time)
    time_info = query.get_query_count_intervals(start_time, end_time)
    total_requests, unique_requests, unique_ips, unique_files, unique_requesters, average_file_size \
        = query.get_general_stats(start_time, end_time)
    return render(request, 'dashboard.html', add_default_context({
        'total_request_count': total_requests,
        'unique_request_count': unique_requests,
        'unique_ips': unique_ips,
        'unique_files': unique_files,
        'unique_requesters': unique_requesters,
        'average_file_size': average_file_size,
        'most_queried_labels': json.dumps(
            [item.name for (item, _) in graph_most_queried]) if graph_most_queried else None,
        'most_queried_data': json.dumps(
            [count for (_, count) in graph_most_queried]) if graph_most_queried else None,
        # 'most_using_labels': json.dumps(list(graph_most_using.values_list('requester', flat=True))),
        # 'most_using_data': json.dumps(list(graph_most_using.values_list('count', flat=True))),
        'time_info_times': json.dumps([reading.time.isoformat() for reading in time_info]) if time_info else None,
        'time_info_counts': json.dumps([reading.count for reading in time_info] if time_info else None)
    }, time_range_form, start_time, end_time))


@cache_page(settings.CACHE_TIME)
def item_dashboard(request, item_name, start_time=START_TIME, end_time=END_TIME):
    if request.method == 'POST':
        time_range_form = SelectTimeRangeForm(request.POST)
        if time_range_form.is_valid():
            return redirect(request.resolver_match.view_name,
                            item_name=item_name,
                            start_time=time_range_form.cleaned_data['start_time'],
                            end_time=time_range_form.cleaned_data['end_time'])
    else:
        time_range_form = SelectTimeRangeForm()
    item = query.get_or_create_item(item_name)
    (request_breakdown, ip_breakdown) = query.get_requesters_for_item(item, start_time, end_time)
    return render(request, 'item_dashboard.html', add_default_context({
        'item': item,
        'request_breakdown': request_breakdown,
        'ip_breakdown': ip_breakdown
    }, time_range_form, start_time, end_time))


@cache_page(settings.CACHE_TIME)
def requester_dashboard(request, requester, start_time=START_TIME, end_time=END_TIME):
    if request.method == 'POST':
        time_range_form = SelectTimeRangeForm(request.POST)
        if time_range_form.is_valid():
            return redirect(request.resolver_match.view_name,
                            requester=requester,
                            start_time=time_range_form.cleaned_data['start_time'],
                            end_time=time_range_form.cleaned_data['end_time'])
    else:
        time_range_form = SelectTimeRangeForm()
    total_downloads, unique_downloads = query.get_stats_for_source(requester=requester)
    return render(request, 'user_dashboard.html', add_default_context({
        'unique_downloads': unique_downloads,
        'total_downloads': total_downloads,
        'requester': requester
    }, time_range_form, start_time, end_time))


@cache_page(settings.CACHE_TIME)
def ip_address_dashboard(request, ip_address, start_time=START_TIME, end_time=END_TIME):
    if request.method == 'POST':
        time_range_form = SelectTimeRangeForm(request.POST)
        if time_range_form.is_valid():
            return redirect(request.resolver_match.view_name,
                            ip_address=ip_address,
                            start_time=time_range_form.cleaned_data['start_time'],
                            end_time=time_range_form.cleaned_data['end_time'])
    else:
        time_range_form = SelectTimeRangeForm()
    total_downloads, unique_downloads = query.get_stats_for_source(start_time, end_time, ip_address=ip_address)
    return render(request, 'ip_address_dashboard.html', add_default_context({
        'unique_downloads': unique_downloads,
        'total_downloads': total_downloads,
        'ip_address': ip_address
    }, time_range_form, start_time, end_time))


@cache_page(settings.CACHE_TIME)
def most_queried_data_table(request, start_time=START_TIME, end_time=END_TIME, page=0):
    page_size = 25
    most_queried = query.get_most_queried_items_limited(page_size, start_time, end_time, page)
    return render(request, 'item_table.html', add_table_context({
        'table_data': most_queried,
        'table_name': 'Most Uniquely Downloaded',
    }, start_time, end_time, page, page_size))


@cache_page(settings.CACHE_TIME)
def biggest_users_data_table(request, start_time=START_TIME, end_time=END_TIME, page=0):
    page_size = 25
    biggest_requesters = query.get_most_active_users_limited(page_size, start_time, end_time, page)
    return render(request, 'user_table.html', add_table_context({
        'table_data': biggest_requesters,
        'table_name': 'Most Active Downloaders',
    }, start_time, end_time, page, page_size))


@cache_page(settings.CACHE_TIME)
def items_for_requester_data_table(request, requester, start_time=START_TIME, end_time=END_TIME, page=0):
    page_size = 25
    items = query.get_items_for_source_limited(page_size, start_time, end_time, page, requester=requester)
    return render(request, 'item_table.html', add_table_context({
        'table_data': items,
        'table_name': 'Most Downloaded',
        'kwargs': {
            'requester': requester
        }
    }, start_time, end_time, page, page_size))


@cache_page(settings.CACHE_TIME)
def items_for_ip_address_data_table(request, ip_address, start_time=START_TIME, end_time=END_TIME, page=0):
    page_size = 25
    items = query.get_items_for_source_limited(page_size, start_time, end_time, page, ip_address=ip_address)
    return render(request, 'item_table.html', add_table_context({
        'table_data': items,
        'table_name': 'Most Downloaded',
        'kwargs': {
            'ip_address': ip_address
        }
    }, start_time, end_time, page, page_size))
