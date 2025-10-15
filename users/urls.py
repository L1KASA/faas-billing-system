from django.urls import path
from . import views

from django.conf.urls.static import static
from django.urls import path, include
from faas_billing import settings

app_name = 'users'

urlpatterns = [
    # Registration
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('register/client/', views.ClientRegistrationView.as_view(), name='register-client'),
    path('register/success/', views.RegistrationSuccessView.as_view(), name='registration_success'),

    # Email verification
    path('verify-email/<uidb64>/<token>/', views.VerifyEmailView.as_view(), name='verify-email'),

    # Authentication
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('dashboard/', views.DashboardView.as_view(), name='dashboard'),

    # Password recovery
    path('password-reset/', views.PasswordResetView.as_view(), name='password-reset'),
    path('password-reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('password-reset/complete/', views.PasswordResetCompleteView.as_view(), name='password-reset-complete'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
