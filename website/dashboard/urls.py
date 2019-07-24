import itertools
import urllib.parse
from datetime import datetime

from django.urls import path, register_converter
from django.utils import timezone

from . import views


class DateRangeConverter:
    FORMAT = '%Y-%m-%d'
    regex = r'[0-9\-]+'

    def to_python(self, value):
        return datetime.strptime(value, self.FORMAT).astimezone(timezone.get_current_timezone())

    def to_url(self, value):
        return value.strftime(self.FORMAT)


class RequesterConverter:
    regex = r'[^\/]+'

    def to_python(self, value):
        return urllib.parse.unquote_plus(value)

    def to_url(self, value):
        return urllib.parse.quote_plus(value)


register_converter(DateRangeConverter, 'datetime')
register_converter(RequesterConverter, 'requester')

app_name = 'dashboard'

urlpatterns = []


def add_urls(path_names, view, name):
    """
    Register URL patterns with the same view and name in Django.
    :param path_names: Paths with different wanted parameters.
    :param view: View to render for all. Must have matching arguments.
    :param name: Name of the view for template access.
    """
    urlpatterns.extend([path(path_name, view, name=name) for path_name in path_names])


def get_ranged(base_path):
    """
    Add a ranged ability to the URL
    :param base_path: URL to build from, must include <range>
    :return: URLs that allowed ranged access. Still need to be added, as they are still just strings.
    """
    return [base_path.replace('<range>/', ''),
            base_path.replace('<range>', '<datetime:start_time>/to/<datetime:end_time>')]


def get_table(base_path):
    """
    Add a pagination ability to a table in addition to a default page.
    :param base_path: URL to build from, must include <page>
    :return: URLs that allow pagination. Still need to be added, as they are still just strings.
    """
    return [base_path.replace('<page>', 'page/<int:page>'), base_path.replace('<page>/', '')]


def get_table_ranged(base_path):
    return itertools.chain.from_iterable([get_ranged(table_url) for table_url in get_table(base_path)])


add_urls(get_ranged('<range>/'), views.dashboard, name='dashboard')
add_urls(get_ranged('requester/<requester:requester>/<range>/'), views.requester_dashboard, name='requester_dashboard')
add_urls(get_ranged('ip_address/<str:ip_address>/<range>/'), views.ip_address_dashboard, name='ip_address_dashboard')
add_urls(get_ranged('item/<str:item_name>/<range>/'), views.item_dashboard, name='item_dashboard')
add_urls(get_table_ranged('most_queried_data_table/<range>/<page>/'), views.most_queried_data_table,
         'most_queried_data_table')
add_urls(get_table_ranged('biggest_users_data_table/<range>/<page>/'), views.biggest_users_data_table,
         'biggest_users_data_table')
add_urls(get_table_ranged('items_for_requester_data_table/<requester:requester>/<range>/<page>/'),
         views.items_for_requester_data_table, 'items_for_requester_data_table')
add_urls(get_table_ranged('items_for_ip_address_data_table/<str:ip_address>/<range>/<page>/'),
         views.items_for_ip_address_data_table, 'items_for_ip_address_data_table')
add_urls(get_ranged('experiment/bernstein/<range>/'), views.bernstein_experiment, 'bernstein_experiment')
add_urls(get_table_ranged('experiment/bernstein/most_queried_data_table/<range>/<page>/'),
         views.bernstein_experiment_most_queried_data_table, 'bernstein_experiment_most_queried_data_table')
add_urls(get_table_ranged('experiment/bernstein/biggest_users_data_table/<range>/<page>/'),
         views.bernstein_experiment_biggest_users_data_table, 'bernstein_experiment_biggest_users_data_table')
