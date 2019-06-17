from django.shortcuts import redirect, render


def root(request):
    return redirect('home')


def home(request):
    return render(request, 'home.html')
