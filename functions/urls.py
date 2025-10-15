from django.urls import path
from . import views

app_name = 'functions'

urlpatterns = [
    path('', views.function_list, name='function_list'),
    path('deploy/', views.deploy_function, name='deploy_function'),
    path('<int:pk>/', views.function_detail, name='function_detail'),
    path('<int:pk>/delete/', views.delete_function, name='delete_function'),
    path('<int:pk>/invoke/', views.invoke_function, name='invoke_function'),
    path('<int:pk>/status/', views.function_status_api, name='function_status_api'),
]
