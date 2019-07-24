import json

from django.conf import settings
from django.shortcuts import render, redirect
from django.views.decorators.cache import cache_page

from activity_viewer.util import time_this
from . import query
from .forms import SelectTimeRangeForm
from .query import START_TIME, END_TIME, BERNSTEIN_EXPERIMENT_FILTER_KWARGS

DEFAULT_PAGE_SIZE = 25
GRAPH_SIZE = 6


def add_range_context(context, time_range_form, start_time, end_time):
    is_default = start_time is START_TIME and end_time is END_TIME
    context.update({
        'is_default': is_default,
        'time_range_form': time_range_form,
        'start_time': None if is_default else start_time,
        'end_time': None if is_default else end_time
    })
    return context


def add_ranged_table_context(context, start_time, end_time, page, page_size):
    add_range_context(context, None, start_time, end_time)
    add_table_context(context, page, page_size)
    return context


def add_table_context(context, page, page_size):
    context.update({
        'table_page': page,
        'table_page_size': page_size
    })
    return context


def add_time_graph_context(context, time_info):
    context.update({
        'time_info_times': json.dumps([reading.time.isoformat() for reading in time_info]) if time_info else None,
        'time_info_counts': json.dumps([reading.count for reading in time_info]) if time_info else None
    })
    return context


@time_this
def add_most_queried_graph_context(context, graph_most_queried):
    item_names, counts = tuple(zip(*graph_most_queried.values_list('item__name', 'count')))
    context.update({
        'most_queried_labels': json.dumps(item_names) if graph_most_queried else None,
        'most_queried_data': json.dumps(counts) if graph_most_queried else None
    })
    return context


def add_statistics_context(context, stats):
    total_requests, unique_requests, unique_ips, unique_files, unique_requesters, average_file_size = stats
    context.update({
        'total_request_count': total_requests,
        'unique_request_count': unique_requests,
        'unique_ips': unique_ips,
        'unique_files': unique_files,
        'unique_requesters': unique_requesters,
        'average_file_size': average_file_size,
    })
    return context


def get_time_range_form(request):
    if request.method == 'POST':
        time_range_form = SelectTimeRangeForm(request.POST)
        if time_range_form.is_valid():
            return time_range_form
    return SelectTimeRangeForm()


def redirect_from_form(request, time_range_form, **kwargs):
    return redirect(request.resolver_match.view_name,
                    **kwargs,
                    start_time=time_range_form.cleaned_data['start_time'],
                    end_time=time_range_form.cleaned_data['end_time'])


@cache_page(settings.CACHE_TIME)
def dashboard(request, start_time=START_TIME, end_time=END_TIME):
    time_range_form = get_time_range_form(request)
    if time_range_form.is_valid():
        return redirect_from_form(request, time_range_form)
    graph_most_queried = query.get_most_queried_items_limited(GRAPH_SIZE, start_time, end_time)
    time_info = query.get_query_count_intervals(start_time, end_time)
    stats = query.get_general_stats(start_time, end_time)
    context = {}
    add_statistics_context(context, stats)
    add_most_queried_graph_context(context, graph_most_queried)
    add_time_graph_context(context, time_info)
    add_range_context(context, time_range_form, start_time, end_time)
    return render(request, 'dashboard.html', context)


@cache_page(settings.CACHE_TIME)
def item_dashboard(request, item_name, start_time=START_TIME, end_time=END_TIME):
    time_range_form = get_time_range_form(request)
    if time_range_form.is_valid():
        return redirect_from_form(request, time_range_form, item_name=item_name)
    item = query.get_item(item_name)
    request_breakdown, ip_breakdown = query.get_requesters_for_item(item, start_time, end_time)
    print(ip_breakdown.values_list('requester', 'ip_address', 'count'))
    return render(request, 'item_dashboard.html', add_range_context({
        'item': item,
        'request_breakdown': request_breakdown.values_list('requester', 'count'),
        'ip_breakdown': ip_breakdown.values_list('requester', 'ip_address', 'count')
    }, time_range_form, start_time, end_time))


def add_source_context(context, unique_downloads, total_downloads, **kwargs):
    context.update({
        'unique_downloads': unique_downloads,
        'total_downloads': total_downloads,
    })
    context.update(kwargs)
    return context


@cache_page(settings.CACHE_TIME)
def requester_dashboard(request, requester, start_time=START_TIME, end_time=END_TIME):
    time_range_form = get_time_range_form(request)
    if time_range_form.is_valid():
        return redirect_from_form(request, time_range_form, requester=requester)
    total_downloads, unique_downloads = query.get_stats_for_source(start_time, end_time, requester=requester)
    context = {}
    add_source_context(context, unique_downloads, total_downloads, requester=requester)
    add_range_context(context, time_range_form, start_time, end_time)
    return render(request, 'user_dashboard.html', context)


@cache_page(settings.CACHE_TIME)
def ip_address_dashboard(request, ip_address, start_time=START_TIME, end_time=END_TIME):
    time_range_form = get_time_range_form(request)
    if time_range_form.is_valid():
        return redirect_from_form(request, time_range_form, ip_address=ip_address)
    total_downloads, unique_downloads = query.get_stats_for_source(start_time, end_time, ip_address=ip_address)
    ip_info = query.get_or_create_ip_info(ip_address)
    context = {
        'ip_isp': ip_info.isp
    }
    add_source_context(context, unique_downloads, total_downloads, ip_address=ip_address)
    add_range_context(context, time_range_form, start_time, end_time)
    return render(request, 'ip_address_dashboard.html', context)


def render_table(request, data, name, template_name, page, start_time=None, end_time=None, page_size=DEFAULT_PAGE_SIZE,
                 **kwargs):
    context = {
        'table_data': data,
        'table_name': name,
        'kwargs': kwargs
    }
    add_table_context(context, page, page_size)
    if start_time and end_time:
        add_range_context(context, None, start_time, end_time)
    return render(request, template_name, context)


@time_this
def render_item_table(request, data, page, start_time=None, end_time=None, page_size=DEFAULT_PAGE_SIZE, **kwargs):
    return render_table(request,
                        data.values_list('item__name', 'item__experiment__name', 'item__experiment__assay_title',
                                         'count'),
                        'Most Uniquely Downloaded', 'ajax_item_table.html', page, start_time, end_time, page_size,
                        **kwargs)


def render_user_table(request, data, page, start_time=None, end_time=None, page_size=DEFAULT_PAGE_SIZE, **kwargs):
    return render_table(request,
                        data.values_list('requester', 'ip_address', 'count'),
                        'Most Active Downloaders', 'ajax_user_table.html', page, start_time, end_time,
                        page_size, **kwargs)


@cache_page(settings.CACHE_TIME)
def most_queried_data_table(request, start_time=START_TIME, end_time=END_TIME, page=0):
    most_queried = query.get_most_queried_items_limited(DEFAULT_PAGE_SIZE, start_time, end_time, page)
    return render_item_table(request, most_queried, page, start_time, end_time)


@cache_page(settings.CACHE_TIME)
def biggest_users_data_table(request, start_time=START_TIME, end_time=END_TIME, page=0):
    biggest_requesters = query.get_most_active_users_limited(DEFAULT_PAGE_SIZE, start_time, end_time, page)
    return render_user_table(request, biggest_requesters, page, start_time, end_time)


@cache_page(settings.CACHE_TIME)
def items_for_requester_data_table(request, requester, start_time=START_TIME, end_time=END_TIME, page=0):
    items = query.get_items_for_source_limited(DEFAULT_PAGE_SIZE, start_time, end_time, page, requester=requester)
    return render_item_table(request, items, page, start_time, end_time, requester=requester)


@cache_page(settings.CACHE_TIME)
def items_for_ip_address_data_table(request, ip_address, start_time=START_TIME, end_time=END_TIME, page=0):
    items = query.get_items_for_source_limited(DEFAULT_PAGE_SIZE, start_time, end_time, page, ip_address=ip_address)
    return render_item_table(request, items, page, start_time, end_time, ip_address=ip_address)


@cache_page(settings.CACHE_TIME)
def bernstein_experiment(request, start_time=START_TIME, end_time=END_TIME):
    relative_access = query.get_relative_access()
    time_range_form = get_time_range_form(request)
    if time_range_form.is_valid():
        return redirect_from_form(request, time_range_form)
    time_info = query.get_query_count_intervals(start_time, end_time, 'bernstein')
    stats = query.get_general_stats(start_time, end_time, **BERNSTEIN_EXPERIMENT_FILTER_KWARGS)
    context = {
        'relative_date_labels': relative_access.axes[0].tolist(),
        'relative_date_data': relative_access.to_json(orient='records')
    }
    add_statistics_context(context, stats)
    add_time_graph_context(context, time_info)
    add_range_context(context, time_range_form, start_time, end_time)
    return render(request, 'bernstein_experiment.html', context)


@cache_page(settings.CACHE_TIME)
def bernstein_experiment_most_queried_data_table(request, start_time=START_TIME, end_time=END_TIME, page=0):
    most_queried = query.get_most_queried_items_limited(DEFAULT_PAGE_SIZE, start_time, end_time,
                                                        **BERNSTEIN_EXPERIMENT_FILTER_KWARGS)
    return render_item_table(request, most_queried, page, start_time, end_time)


@cache_page(settings.CACHE_TIME)
def bernstein_experiment_biggest_users_data_table(request, start_time=START_TIME, end_time=END_TIME, page=0):
    biggest_users = query.get_most_active_users_limited(DEFAULT_PAGE_SIZE, start_time, end_time, page,
                                                        **BERNSTEIN_EXPERIMENT_FILTER_KWARGS)
    return render_user_table(request, biggest_users, page, start_time, end_time)
