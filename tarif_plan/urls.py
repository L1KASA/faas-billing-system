from django.urls import path
from . import views

app_name = 'tarif_plan'

urlpatterns = [
    path('plans/', views.subscription_plans, name='subscription_plans'),
    path('change/', views.change_subscription, name='change_subscription'),
]