from datetime import datetime

from django.urls import path, register_converter

from . import views


class DateRangeConverter:
    FORMAT = '%Y-%m-%d-%H-%M-%S-%f'
    regex = '[0-9\-]+'

    def to_python(self, value):
        return datetime.strftime(value.start, self.FORMAT)

    def to_url(self, value):
        return value.strftime(self.FORMAT)


register_converter(DateRangeConverter, 'datetime')

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('<datetime:start>/to/<datetime:end>', views.dashboard, name='dashboard_range'),
    path('items/<str:item_name>', views.item_dashboard, name='item_dashboard')
]
