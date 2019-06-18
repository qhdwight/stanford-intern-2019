from django.shortcuts import redirect, render

from . import crawler


def dashboard(request):
    return render(request, 'dashboard.html')


def crawl(request):
    crawler.crawl()
    return redirect('dashboard:dashboard')
