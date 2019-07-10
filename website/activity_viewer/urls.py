from django.contrib import admin
from django.urls import include, path

from . import views

urlpatterns = [
    # Include admin URLs. This is where we can view raw objects from the database.
    path('admin/', admin.site.urls),
    # Redirects to home of dashboard app
    path('', views.root, name='root'),
    # Include all of the dashboard urls
    path('dashboard/', include('dashboard.urls', namespace='dashboard'), name='dashboard'),
]
