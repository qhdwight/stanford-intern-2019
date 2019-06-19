from django.shortcuts import redirect, render

from . import extractor


def dashboard(request):
    return render(request, 'dashboard.html')


def crawl(request):
    extractor.extract_from_local_into_database()
    return redirect('dashboard:dashboard')
