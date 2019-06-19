from django.shortcuts import redirect, render

from .models import Log


def dashboard(request):
    request_count = Log.objects.count()
    return render(request, 'dashboard.html', {
        'request_count' : request_count
    })
