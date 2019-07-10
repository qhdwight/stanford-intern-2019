from django.shortcuts import redirect


def root(request):
    """
    Request to base host name will just redirect to dashboard app
    """
    return redirect('dashboard:dashboard')
