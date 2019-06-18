from django.contrib import admin
from django.urls import include, path

from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.root, name='root'),
    path('dashboard/', include('dashboard.urls', namespace='dashboard'), name='dashboard'),
]
