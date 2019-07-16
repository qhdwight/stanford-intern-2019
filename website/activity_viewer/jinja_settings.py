import locale
from itertools import zip_longest

from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from jinja2 import Environment

from dashboard.query import get_encode_url

locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')


def render_field_with_class(field, css_class_name):
    """
    Adds an entry to the class definition of the HTML element created.
    This is used for special rendering of incorrect fields or other special cases in general on forms.
    :param field: Django field
    :param css_class_name: Class name to add
    :return: The passed in Django field
    """
    if 'class' in field.field.widget.attrs:
        field.field.widget.attrs['class'] += ' ' + css_class_name
    else:
        field.field.widget.attrs['class'] = css_class_name
    return field


def locale_format(string):
    """
    Formats a number nicely with commas
    """
    return f'{string:n}'


def url_range_aware(view_name, start_time=None, end_time=None, kwargs=None):
    """
    Given a view name, return a url that has start and end times if present (all data).
    Default time ranges will not have times specified in URL to make them appear cleaner.
    :param view_name: Name of view, including app name as well
    :param start_time: Start time of query range in database
    :param end_time: End time of query range in database
    :param kwargs: Keyword arguments that get passed to the url. This is useful if the view has unique parameters.
    :return: A URL that is properly shortened if default and still has URL parameters attached
    """
    if start_time or end_time:
        # We are a specific range of time and must update the URL keyword arguments to resolve properly
        if kwargs is None:
            kwargs = {}
        kwargs.update({
            'start_time': start_time,
            'end_time': end_time
        })
    return reverse(view_name, kwargs=kwargs)


def environment(**options):
    """
    This gives us the ability to link functions in python to the global namespace in Jinja
    So, we can call the specified functions below by their key name in dictionary in any template.
    """
    env = Environment(**options)
    # print(env.lstrip_blocks, env.trim_blocks)
    env.globals.update({
        'static': staticfiles_storage.url,
        'url': reverse,
        'url_range_aware': url_range_aware,
        'render_field_with_class': render_field_with_class,
        'get_encode_url': get_encode_url,
        'zip': zip,
        'zip_longest': zip_longest,
        'locale_format': locale_format
    })
    return env
