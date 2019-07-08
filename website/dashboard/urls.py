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


def add_ranged(base_path, view, name):
    ranged_path = base_path.replace('<range>', '<datetime:start_time>/to/<datetime:end_time>')
    default_path = base_path.replace('<range>/', '')
    urlpatterns.extend((path(default_path, view, name=name),
                        path(ranged_path, view, name=name)))


def add_table_ranged(base_path, view, name):
    add_ranged(base_path.replace('<page>', '<int:page>'), view, name)
    add_ranged(base_path.replace('<page>/', ''), view, name)


add_ranged('<range>/', views.dashboard, name='dashboard')
add_ranged('requester/<requester:requester>/<range>/', views.requester_dashboard, name='requester_dashboard')
add_ranged('ip_address/<str:ip_address>/<range>/', views.ip_address_dashboard, name='ip_address_dashboard')
add_ranged('item/<str:item_name>/<range>/', views.item_dashboard, name='item_dashboard')
add_table_ranged('most_queried_data_table/<range>/<page>/', views.most_queried_data_table, 'most_queried_data_table')
add_table_ranged('biggest_users_data_table/<range>/<page>/', views.biggest_users_data_table, 'biggest_users_data_table')
add_table_ranged('items_for_requester_data_table/<requester:requester>/<range>/<page>/',
                 views.items_for_requester_data_table, 'items_for_requester_data_table')
add_table_ranged('items_for_ip_address_data_table/<str:ip_address>/<range>/<page>/',
                 views.items_for_ip_address_data_table, 'items_for_ip_address_data_table')
