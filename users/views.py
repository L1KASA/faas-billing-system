import logging

from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import View, FormView, TemplateView
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpRequest, HttpResponse
from django import forms
from typing import Any, Dict
from django.db import models

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


class DashboardView(TemplateView):
    """Dashboard view"""
    template_name: str = 'users/dashboard.html'

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        """Add user to context"""
        context: Dict[str, Any] = super().get_context_data(**kwargs)
        context['user'] = self.request.user
        return context
