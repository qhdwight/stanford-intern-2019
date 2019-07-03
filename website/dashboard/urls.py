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
    urlpatterns.extend((path(base_path, view, name=name),
                        path(f'{base_path}<datetime:start_time>/to/<datetime:end_time>/', view, name=f'{name}_range')))


add_ranged('', views.dashboard, name='dashboard')
add_ranged('requester/<requester:requester>/', views.requester_dashboard, name='requester_dashboard')
add_ranged('ip_address/<str:ip_address>/', views.ip_address_dashboard, name='ip_address_dashboard')
add_ranged('item/<str:item_name>/', views.item_dashboard, name='item_dashboard')
# add_ranged('item/data_table/<str:item_name>', views.item_data_table, name='item_data_table')
