from django.db.models import Count
from django.shortcuts import render

from .models import Log
import json


def dashboard(request):
    request_count = Log.objects.count()
    most_queried_s3_keys = Log.objects.all().values('s3_key').annotate(total=Count('s3_key')).order_by('-total')[:6]
    header_json = json.dumps([s3_key.split('/')[-1] for s3_key in most_queried_s3_keys.values_list('s3_key', flat=True)])
    data_json = json.dumps(list(most_queried_s3_keys.values_list('total', flat=True)))
    return render(request, 'dashboard.html', {
        'request_count': request_count,
        'header_json': header_json,
        'data_json': data_json
    })
