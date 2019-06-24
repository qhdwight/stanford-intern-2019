from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from jinja2 import Environment

from dashboard.models import get_file_name, get_encode_url


def render_field_with_class(field, css_class_name):
    if 'class' in field.field.widget.attrs:
        field.field.widget.attrs['class'] += ' ' + css_class_name
    else:
        field.field.widget.attrs['class'] = css_class_name
    return field


def environment(**options):
    env = Environment(**options)
    env.globals.update({
        'static': staticfiles_storage.url,
        'url': reverse,
        'render_field_with_class': render_field_with_class,
        'render_s3_key': get_file_name,
        'get_encode_url': get_encode_url,
        'zip': zip
    })
    return env
