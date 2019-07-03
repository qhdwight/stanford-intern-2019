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

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('<datetime:start_time>/to/<datetime:end_time>', views.dashboard, name='dashboard_range'),
    path('item/<str:item_name>', views.item_dashboard, name='item_dashboard'),
    path('item/<str:item_name>/<datetime:start_time>/to/<datetime:end_time>', views.item_dashboard,
         name='item_dashboard_range'),
    path('requester/<requester:requester>', views.requester_dashboard, name='requester_dashboard'),
    path('requester/<requester:requester>/<datetime:start_time>/to/<datetime:end_time>', views.requester_dashboard,
         name='requester_dashboard_range'),
    path('ip_address/<str:ip_address>', views.ip_address_dashboard, name='ip_address_dashboard'),
    path('ip_address/<str:ip_address>/<datetime:start_time>/to/<datetime:end_time>', views.ip_address_dashboard, name='ip_address_dashboard_range')
]
