import random
import string
from typing import Any, Dict

from django.core.mail import send_mail
from django.db import DatabaseError
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.conf import settings
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.core.cache import cache
import logging

from .exceptions import EmailSendingError, UserRegistrationError, InvalidTokenError
from .models import User, ClientUser
from faas_billing.config import config

logger = logging.getLogger(__name__)


class PasswordRecoveryService:
    """Service for password recovery operations"""

    @staticmethod
    def generate_recovery_code(length: int = config.PASSWORD_RECOVERY_CODE_LENGTH) -> str:
        """Generate numeric recovery code"""
        return ''.join(random.choices(string.digits, k=length))

    @staticmethod
    def store_recovery_code(email: str, code: str) -> None:
        """Store recovery code in cache with timeout from config"""
        cache_key = f"password_recovery_{email}"
        cache.set(cache_key, code, timeout=config.PASSWORD_RECOVERY_TIMEOUT)

    @staticmethod
    def validate_recovery_code(email: str, code: str) -> bool:
        """Validate recovery code"""
        cache_key = f"password_recovery_{email}"
        stored_code = cache.get(cache_key)
        return stored_code == code

    @staticmethod
    def delete_recovery_code(email: str) -> None:
        """Delete used recovery code"""
        cache_key = f"password_recovery_{email}"
        cache.delete(cache_key)


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Token generator for email verification"""

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{timestamp}{user.email_verified}{user.is_active}"


email_verification_token = EmailVerificationTokenGenerator()


class EmailService:
    """Service for handling email operations"""

    @staticmethod
    def send_verification_email(user: User, request: HttpRequest) -> bool:
        """Send email verification message"""
        try:
            token = email_verification_token.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))

            verification_url = request.build_absolute_uri(
                reverse('users:verify-email', kwargs={'uidb64': uid, 'token': token})
            )

            context = {
                'user': user,
                'verification_url': verification_url,
                'site_name': getattr(settings, 'SITE_NAME', 'Your Site')
            }

            html_message = render_to_string(config.EMAIL_TEMPLATE_VERIFICATION, context)
            plain_message = strip_tags(html_message)

            send_mail(
                subject=config.EMAIL_SUBJECT_VERIFICATION,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )

            logger.info(f"Verification email sent to {user.email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send verification email to {user.email}: {str(e)}")
            raise EmailSendingError(f"Failed to send verification email: {str(e)}")

    @staticmethod
    def send_welcome_email(user: User) -> bool:
        """Send welcome email after verification"""
        try:
            context = {
                'user': user,
                'site_name': getattr(settings, 'SITE_NAME', 'Your Site')
            }

            html_message = render_to_string(config.EMAIL_TEMPLATE_WELCOME, context)
            plain_message = strip_tags(html_message)

            send_mail(
                subject=config.EMAIL_SUBJECT_WELCOME,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )

            logger.info(f"Welcome email sent to {user.email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")
            raise EmailSendingError(f"Failed to send welcome email: {str(e)}")

    @staticmethod
    def send_recovery_code(email: str, code: str) -> bool:
        """Send password recovery code"""
        try:
            context = {
                'code': code,
                'site_name': getattr(settings, 'SITE_NAME', 'Your Site')
            }

            html_message = render_to_string(config.EMAIL_TEMPLATE_RECOVERY, context)
            plain_message = strip_tags(html_message)

            send_mail(
                subject=config.EMAIL_SUBJECT_RECOVERY,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                html_message=html_message,
                fail_silently=False,
            )

            logger.info(f"Recovery code sent to {email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send recovery code to {email}: {str(e)}")
            raise EmailSendingError(f"Failed to send recovery code: {str(e)}")


class UserRegistrationService:
    """Service for user registration operations"""

    @staticmethod
    def register_user(
        user_data: Dict[str, Any],
        request: HttpRequest = None,
        user_type: str ='regular'
    ) -> User:
        """Register a new user and send verification email"""
        from django.db import transaction

        try:
            with transaction.atomic():
                user = User.objects.create_user(**user_data)
                user.is_active = False  # Deactivate until email verification
                user.save()

                if user_type == 'client':
                    ClientUser.objects.create(user=user)

                if request:
                    EmailService.send_verification_email(user, request)

                return user
        except DatabaseError as e:
            logger.error(f"Database error during user registration: {str(e)}")
            raise UserRegistrationError(f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during user registration: {str(e)}")
            raise UserRegistrationError(f"Registration failed: {str(e)}")

    @staticmethod
    def verify_email(uidb64: str, token: str) -> User:
        """Verify user email"""
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, ObjectDoesNotExist):
            raise InvalidTokenError("Invalid verification link")

        if email_verification_token.check_token(user, token):
            user.email_verified = True
            user.is_active = True
            user.save()

            EmailService.send_welcome_email(user)
            return user

        raise InvalidTokenError("Invalid or expired verification link")
