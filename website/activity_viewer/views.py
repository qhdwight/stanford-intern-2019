from django.shortcuts import redirect, render


def root(request):
    return redirect('dashboard:dashboard')
