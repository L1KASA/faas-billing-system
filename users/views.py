import logging
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import View, FormView, TemplateView
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse
from django import forms
from typing import Any, Dict, Optional

from billing.billing_calculator import BillingCalculator
from billing.metrics_manager import SimpleMetricsManager
from tarif_plan.models import TariffPlan
from tarif_plan.subscription_manager import SubscriptionManager
from .forms import (
    UserRegistrationForm,
    ClientRegistrationForm,
    EmailAuthenticationForm,
    PasswordResetForm,
    PasswordResetConfirmForm
)
from .models import User
from .exceptions import EmailSendingError
from .services import EmailService, UserRegistrationService, PasswordRecoveryService
from functions.models import Function

logger = logging.getLogger(__name__)


class RegistrationView(FormView):
    """Base registration view"""
    template_name: str = 'users/register.html'
    success_url = reverse_lazy('users:registration_success')

    def form_valid(self, form: forms.Form) -> HttpResponse:
        """Handle valid form submission"""
        user: Optional[User] = None
        try:
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            EmailService.send_verification_email(user, self.request)

            self.request.session['registered_email'] = user.email
            return super().form_valid(form)

        except EmailSendingError as e:
            logger.error(f"Email sending error: {str(e)}")
            if user:
                self.request.session['registered_email'] = user.email
                messages.warning(self.request,
                                 'Registration successful, but verification email could not be sent. Please contact support.')
                return super().form_valid(form)
            else:
                messages.error(self.request, 'Registration failed. Please try again.')
                return self.form_invalid(form)
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            messages.error(self.request, 'An error occurred during registration. Please try again.')
            return self.form_invalid(form)


class UserRegistrationView(RegistrationView):
    """Regular user registration"""
    form_class = UserRegistrationForm

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """Add user_type to context"""
        context: Dict[str, Any] = super().get_context_data(**kwargs)
        context['user_type'] = 'regular'
        return context


class ClientRegistrationView(RegistrationView):
    """Client user registration"""
    form_class = ClientRegistrationForm
    template_name: str = 'users/register_client.html'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """Add user_type to context"""
        context: Dict[str, Any] = super().get_context_data(**kwargs)
        context['user_type'] = 'client'
        return context


class RegistrationSuccessView(TemplateView):
    """Registration success page"""
    template_name: str = 'users/registration_success.html'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """Add email to context"""
        context: Dict[str, Any] = super().get_context_data(**kwargs)
        context['email'] = self.request.session.get('registered_email', '')
        return context


class VerifyEmailView(View):
    """Email verification view"""

    def get(self, request: HttpRequest, uidb64: str, token: str) -> HttpResponse:
        """Handle email verification"""
        try:
            user: User = UserRegistrationService.verify_email(uidb64, token)

            messages.success(request, 'Your email has been successfully verified. You can now log in.')
            return redirect('users:login')

        except Exception as e:
            logger.error(f"Email verification error: {str(e)}")
            messages.error(request, 'The verification link is invalid or has expired.')
            return redirect('users:resend-verification')


class LoginView(FormView):
    """Custom login view"""
    template_name: str = 'users/login.html'
    form_class = EmailAuthenticationForm
    success_url = reverse_lazy('users:dashboard')

    def form_valid(self, form: forms.Form) -> HttpResponse:
        """Handle valid login form"""
        email: str = form.cleaned_data['username']
        password: str = form.cleaned_data['password']

        user: Optional[User] = authenticate(self.request, email=email, password=password)

        if user is not None:
            if not user.email_verified:
                messages.error(self.request, 'Please verify your email before logging in.')
                return self.form_invalid(form)

            login(self.request, user)
            messages.success(self.request, f'Welcome back, {user.first_name}!')
            return super().form_valid(form)
        else:
            messages.error(self.request, 'Invalid email or password.')
            return self.form_invalid(form)


class LogoutView(View):
    """Custom logout view"""

    def get(self, request: HttpRequest) -> HttpResponse:
        """Handle logout"""
        logout(request)
        messages.success(request, 'You have been successfully logged out.')
        return redirect('users:login')


@method_decorator(login_required, name='dispatch')
class ProfileView(TemplateView):
    """User profile view"""
    template_name: str = 'users/profile.html'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """Add user to context"""
        context: Dict[str, Any] = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context


class PasswordResetView(FormView):
    """View for initiating password reset"""
    template_name: str = 'users/password_reset.html'
    form_class = PasswordResetForm
    success_url = reverse_lazy('users:password-reset-confirm')

    def form_valid(self, form: forms.Form) -> HttpResponse:
        """Handle password reset request"""
        email: str = form.cleaned_data['email']

        try:
            # Check if user exists
            user: User = User.objects.get(email=email)

            # Generate and send recovery code
            code: str = PasswordRecoveryService.generate_recovery_code()
            PasswordRecoveryService.store_recovery_code(email, code)
            EmailService.send_recovery_code(email, code)

            # Store email in session for next step
            self.request.session['recovery_email'] = email

            messages.info(self.request, f'Recovery code sent to {email}')

        except ObjectDoesNotExist:
            # Don't reveal whether email exists
            messages.info(self.request, 'If this email is registered, you will receive a recovery code.')
            self.request.session['recovery_email'] = email

        return super().form_valid(form)


class PasswordResetConfirmView(FormView):
    """View for confirming password reset with code"""
    template_name: str = 'users/password_reset_confirm.html'
    form_class = PasswordResetConfirmForm
    success_url = reverse_lazy('users:password-reset-complete')

    def get_initial(self) -> Dict[str, Any]:
        """Pre-populate email from session"""
        initial: Dict[str, Any] = super().get_initial()
        initial['email'] = self.request.session.get('recovery_email', '')
        return initial

    def form_valid(self, form: forms.Form) -> HttpResponse:
        """Handle password reset confirmation"""
        email: str = form.cleaned_data['email']
        code: str = form.cleaned_data['code']
        new_password: str = form.cleaned_data['new_password']

        # Validate recovery code
        if not PasswordRecoveryService.validate_recovery_code(email, code):
            form.add_error('code', 'Invalid or expired recovery code.')
            return self.form_invalid(form)

        try:
            # Update user password
            user: User = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()

            # Delete used code
            PasswordRecoveryService.delete_recovery_code(email)

            # Clear session
            if 'recovery_email' in self.request.session:
                del self.request.session['recovery_email']

            messages.success(self.request, 'Password reset successfully! You can now login with your new password.')

        except ObjectDoesNotExist:
            messages.error(self.request, 'User not found.')
            return self.form_invalid(form)

        return super().form_valid(form)


class PasswordResetCompleteView(TemplateView):
    """Password reset completion page"""
    template_name: str = 'users/password_reset_complete.html'


@method_decorator(login_required, name='dispatch')
class DashboardView(TemplateView):
    """Dashboard view with real-time billing"""
    template_name: str = 'users/dashboard.html'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """Add user, billing, and subscription data to context"""
        context: Dict[str, Any] = super().get_context_data(**kwargs)
        user = self.request.user

        context['user'] = user

        try:
            # Информация о подписке
            current_subscription = SubscriptionManager.get_active_subscription(user)
            current_plan = current_subscription.tariff_plan if current_subscription else None
            context['current_subscription'] = current_subscription
            context['current_plan'] = current_plan

            # Доступные тарифные планы
            plans = TariffPlan.objects.filter(is_active=True).order_by('monthly_price')
            context['plans'] = plans

            # Использование ресурсов
            calculator = BillingCalculator(user)
            usage = calculator._get_current_usage()
            context['usage'] = usage

            # Функции пользователя
            user_functions = Function.objects.filter(user=user)
            context['user_functions'] = user_functions

            # Расчет стоимости в реальном времени для каждой функции
            total_monthly_cost = Decimal('0.00')
            function_costs = []

            for function in user_functions:
                try:
                    # Пытаемся получить кэшированные стоимости
                    cached_costs = SimpleMetricsManager.get_cached_costs(function, user)

                    if not cached_costs:
                        # Если нет в кэше, рассчитываем сейчас
                        costs = SimpleMetricsManager.calculate_function_cost_now(function, user)
                        if costs:
                            cached_costs = {
                                'costs': {k: float(v['total_cost']) for k, v in costs.items()},
                                'detailed_costs': costs,
                                'updated_at': timezone.now().isoformat()
                            }

                    if cached_costs:
                        monthly_cost = Decimal(str(cached_costs['costs']['month']))
                        total_monthly_cost += monthly_cost

                        function_costs.append({
                            'function': function,
                            'monthly_cost': monthly_cost,
                            'costs': cached_costs['costs'],
                            'detailed_costs': cached_costs.get('detailed_costs', {}),
                            'updated_at': cached_costs.get('updated_at', 'Never')
                        })
                    else:
                        # Резервный расчет если все остальное не сработало
                        function_metrics = function.metrics.copy() if function.metrics else {
                            'total_cpu_request': function.min_scale * 1000,
                            'total_memory_request': getattr(function, 'memory_request', 536870912),
                            'overall_efficiency': 80,
                            'cold_start_count': 0
                        }

                        cost_breakdown = calculator.calculate_function_cost(
                            function_metrics,
                            Decimal('720')  # 30 дней
                        )

                        monthly_cost = cost_breakdown['total_cost']
                        total_monthly_cost += monthly_cost

                        function_costs.append({
                            'function': function,
                            'monthly_cost': monthly_cost,
                            'costs': {
                                'minute': float(cost_breakdown['total_cost'] / 720 / 24 / 60),
                                'hour': float(cost_breakdown['total_cost'] / 720 / 24),
                                'day': float(cost_breakdown['total_cost'] / 720),
                                'month': float(monthly_cost)
                            },
                            'detailed_costs': {'month': cost_breakdown},
                            'updated_at': 'Calculated now'
                        })

                except Exception as e:
                    logger.warning(f"Error processing function {function.name}: {str(e)}")
                    continue

            context['total_monthly_cost'] = total_monthly_cost
            context['function_costs'] = function_costs

            # Расчет использования в процентах
            if current_plan:
                usage_percentage = {
                    'functions': min((usage['functions_count'] / current_plan.max_functions) * 100,
                                     100) if current_plan.max_functions else 0,
                    'cpu': min((usage['total_cpu'] / current_plan.max_cpu_per_function) * 100,
                               100) if current_plan.max_cpu_per_function else 0,
                    'memory': min((usage['total_memory'] / current_plan.max_memory_per_function) * 100,
                                  100) if current_plan.max_memory_per_function else 0,
                }
                context['usage_percentage'] = usage_percentage

        except Exception as e:
            logger.error(f"Error loading dashboard data: {str(e)}")
            # Устанавливаем значения по умолчанию в случае ошибки
            context['current_subscription'] = None
            context['current_plan'] = None
            context['plans'] = TariffPlan.objects.none()
            context['usage'] = {'functions_count': 0, 'total_cpu': 0, 'total_memory': 0}
            context['user_functions'] = Function.objects.none()
            context['total_monthly_cost'] = Decimal('0.00')
            context['function_costs'] = []
            context['usage_percentage'] = {'functions': 0, 'cpu': 0, 'memory': 0}

        return context