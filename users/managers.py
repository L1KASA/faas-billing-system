from typing import Any, Optional

from django.contrib.auth.models import BaseUserManager
from django.utils.translation import gettext_lazy as _

class UserManager(BaseUserManager):
    """Custom manager for User model with email as username"""
    use_in_migrations = True

    def _create_user(
        self,
        email: str,
        password: Optional[str],
        **extra_fields: Any,
    ):
        """Create and save a user with the given email and password."""
        if not email:
            raise ValueError(_('The Email field must be set'))

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(
        self,
        email: str,
        password: Optional[str] = None,
        **extra_fields: Any,
    ):
        """Create and return a regular user with email"""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        extra_fields.setdefault('is_active', True)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(
        self,
        email: str,
        password: str = None,
        **extra_fields: Any
    ):
        """Create and return a superuser"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))

        return self._create_user(email, password, **extra_fields)

    def get_by_natural_key(self, email: str):
        """Allow authentication with email"""
        return self.get(email=email)


class ClientUserManager(BaseUserManager):
    """Manager for ClientUser model"""

    def create_client(
        self, email: str, password: str = None, **extra_fields: Any
    ):
        """Create a client"""
        from django.db import transaction
        from django.contrib.auth import get_user_model

        User = get_user_model()

        with transaction.atomic():
            user = User.objects.create_user(
                email=email,
                password=password,
                **{k: v for k, v in extra_fields.items() if k in ['first_name', 'last_name', 'second_name', 'phone']}
            )
            client_profile = self.model(
                user=user,
                company=extra_fields.get('company'),
                email_notifications=extra_fields.get('email_notifications', True)
            )
            client_profile.save()
            return user

    def active_clients(self):
        """Return active client users"""
        return self.filter(user__is_active=True)


class EmployeeUserManager(BaseUserManager):
    """Manager for EmployeeUser model"""

    def create_employee(
        self, email: str, password: str = None, **extra_fields: Any
    ):
        """Create an employee user"""
        from django.db import transaction
        from django.contrib.auth import get_user_model

        User = get_user_model()

        with transaction.atomic():
            user = User.objects.create_user(
                email=email,
                password=password,
                is_staff=True,
                **{k: v for k, v in extra_fields.items() if k in ['first_name', 'last_name', 'second_name', 'phone']}
            )
            employee_profile = self.model(
                user=user,
                department=extra_fields.get('department'),
                role=extra_fields.get('role', self.model.StaffRoles.SUPPORT)
            )
            employee_profile.save()
            return user
