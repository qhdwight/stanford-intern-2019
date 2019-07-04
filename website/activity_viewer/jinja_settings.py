import locale
from itertools import zip_longest

from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from jinja2 import Environment

from dashboard.models import get_item_name
from dashboard.query import get_encode_url, START_TIME, END_TIME

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')


def render_field_with_class(field, css_class_name):
    if 'class' in field.field.widget.attrs:
        field.field.widget.attrs['class'] += ' ' + css_class_name
    else:
        field.field.widget.attrs['class'] = css_class_name
    return field


def locale_format(string):
    return f'{string:n}'


def url_range_aware(link, start_time, end_time, kwargs=None):
    if start_time is START_TIME and end_time is END_TIME:
        return reverse(link, kwargs=kwargs)
    else:
        if kwargs is None:
            kwargs = {}
        kwargs.update({
            'start_time': start_time,
            'end_time': end_time
        })
        return reverse(f'{link}_range', kwargs=kwargs)


def environment(**options):
    env = Environment(**options)
    env.globals.update({
        'static': staticfiles_storage.url,
        'url': reverse,
        'url_range_aware': url_range_aware,
        'render_field_with_class': render_field_with_class,
        'render_s3_key': get_item_name,
        'get_encode_url': get_encode_url,
        'zip': zip,
        'zip_longest': zip_longest,
        'locale_format': locale_format
    })
    return env
