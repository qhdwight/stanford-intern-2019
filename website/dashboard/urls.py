from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('items/<str:item_name>', views.item_dashboard, name='item_dashboard')
]
