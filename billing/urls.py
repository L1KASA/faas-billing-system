from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    path('dashboard/', views.realtime_dashboard, name='realtime_dashboard'),
    path('history/', views.billing_history, name='billing_history'),
]