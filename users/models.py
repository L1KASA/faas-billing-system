from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ObjectDoesNotExist
from .managers import UserManager, ClientUserManager, EmployeeUserManager


class User(AbstractUser):
    """Default user model"""
    class UserCurrency(models.TextChoices):

        USD = 'USD', 'US Dollar'
        EUR = 'EUR', 'Euro'
        RUB = 'RUB', 'Russian Ruble'
        BYN = 'BYN', 'Belarusian Ruble'
        KZT = 'KZT', 'Kazakhstani Tenge'
        UAH = 'UAH', 'Ukrainian Hryvnia'
        CNY = 'CNY', 'Chinese Yuan'
        JPY = 'JPY', 'Japanese Yen'

    username = None
    email = models.EmailField(
        unique=True,
        null=False,
        blank=False,
        verbose_name='Email Address',
    )
    first_name = models.CharField(
        max_length=150,
        null=False,
        blank=False,
        verbose_name='First Name',
    )
    last_name = models.CharField(
        max_length=150,
        null=False,
        blank=False,
        verbose_name='Last Name',
    )
    second_name = models.CharField(
        null=True,
        blank=True,
        max_length=150,
        verbose_name='Second Name',
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        unique=True,
        verbose_name='Phone Number',
    )
    email_verified = models.BooleanField(
        default=False,
        verbose_name='Email verified',
    )
    currency = models.CharField(
        max_length=3,
        choices=UserCurrency.choices,
        default=UserCurrency.USD,
        verbose_name='Currency',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Created at')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Updated at')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


    objects = UserManager()

    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    @property
    def full_name(self):
        """Full name of user"""
        names = [str(self.first_name), str(self.second_name), str(self.last_name)]
        return " ".join(filter(None, names)).strip()

    @property
    def user_type(self):
        """Return user type based on related profiles"""
        if hasattr(self, 'client'):
            return 'CLIENT'
        elif hasattr(self, 'employee'):
            return 'EMPLOYEE'
        elif self.is_superuser:
            return 'ADMIN'
        return 'UNKNOWN'

    @property
    def is_client(self):
        return hasattr(self, 'client')

    @property
    def is_employee(self):
        return hasattr(self, 'employee')

    @property
    def is_admin(self):
        return self.is_superuser


class ClientUser(models.Model):
    """Model for client user"""
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='client',
    )
    company = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Company',
    )
    email_notifications = models.BooleanField(
        default=True,
        verbose_name='Email notifications',
    )

    objects = ClientUserManager()

    class Meta:
        db_table = 'user_clients'


class EmployeeUser(models.Model):
    """Model for staff user"""
    class StaffRoles(models.TextChoices):
        MANAGER = 'MANAGER', 'Manager'
        SUPPORT = 'SUPPORT', 'Support'

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='employee'
    )
    department = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='Department',
    )
    role = models.CharField(
        max_length=20,
        choices=StaffRoles.choices,
        default=StaffRoles.SUPPORT,
        verbose_name='Employee Role',
    )

    objects = EmployeeUserManager()

    class Meta:
        db_table = 'user_employees'

    @property
    def is_manager(self):
        return self.role == self.StaffRoles.MANAGER

    @property
    def is_support(self):
        return self.role == self.StaffRoles.SUPPORT
