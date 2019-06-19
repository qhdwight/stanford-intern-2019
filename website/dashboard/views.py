from django.shortcuts import redirect, render

from . import extractor

from .models import Log


def dashboard(request):
    request_count = Log.objects.count()
    return render(request, 'dashboard.html', {
        'request_count' : request_count
    })


def crawl(request):
    extractor.extract_from_local_into_database()
    return redirect('dashboard:dashboard')
