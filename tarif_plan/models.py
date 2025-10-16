from django.db import models
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()


class TariffPlan(models.Model):
    """Тарифные планы для пользователей"""

    class PlanTier(models.TextChoices):
        STARTER = 'STARTER', 'Starter'
        PROFESSIONAL = 'PROFESSIONAL', 'Professional'
        ENTERPRISE = 'ENTERPRISE', 'Enterprise'

    name = models.CharField(max_length=100, unique=True)
    tier = models.CharField(max_length=20, choices=PlanTier.choices, unique=True)
    description = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    # Базовые тарифы ($ за час)
    cpu_rate_per_hour = models.DecimalField(
        max_digits=10, decimal_places=6, default=Decimal('0.002')
    )
    memory_rate_per_gb_hour = models.DecimalField(
        max_digits=10, decimal_places=6, default=Decimal('0.001')
    )
    cold_start_penalty = models.DecimalField(
        max_digits=10, decimal_places=6, default=Decimal('0.005')
    )

    # Коэффициенты
    platform_fee_rate = models.DecimalField(
        max_digits=5, decimal_places=3, default=Decimal('1.3')
    )
    min_efficiency_factor = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal('0.7')
    )
    max_efficiency_factor = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal('1.3')
    )

    # Лимиты
    max_functions = models.IntegerField(default=10)
    max_cpu_per_function = models.IntegerField(default=2000)  # millicores
    max_memory_per_function = models.BigIntegerField(default=2147483648)  # 2GB
    max_scale = models.IntegerField(default=10)

    # Дополнительные функции
    includes_support = models.BooleanField(default=False)
    includes_analytics = models.BooleanField(default=False)
    includes_sla = models.BooleanField(default=False)

    # Цена плана ($ в месяц)
    monthly_price = models.DecimalField(
        max_digits=8, decimal_places=2, default=Decimal('0.00')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} (${self.monthly_price}/month)"


class UserSubscription(models.Model):
    """Подписка пользователя на тарифный план"""

    class SubscriptionStatus(models.TextChoices):
        ACTIVE = 'ACTIVE', 'Active'
        SUSPENDED = 'SUSPENDED', 'Suspended'
        CANCELLED = 'CANCELLED', 'Cancelled'
        EXPIRED = 'EXPIRED', 'Expired'

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='usersubscription'
    )
    tariff_plan = models.ForeignKey(TariffPlan, on_delete=models.PROTECT)
    status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.ACTIVE
    )

    # Период подписки
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(null=True, blank=True)

    # Автопродление
    auto_renew = models.BooleanField(default=True)

    # Использование за текущий период
    functions_used = models.IntegerField(default=0)
    cpu_used = models.IntegerField(default=0)  # millicores
    memory_used = models.IntegerField(default=0)  # bytes

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def is_active(self):
        return self.status == self.SubscriptionStatus.ACTIVE

    @property
    def usage_percentage(self):
        """Процент использования ресурсов"""
        plan = self.tariff_plan
        cpu_pct = (self.cpu_used / plan.max_cpu_per_function) * 100 if plan.max_cpu_per_function else 0
        memory_pct = (self.memory_used / plan.max_memory_per_function) * 100 if plan.max_memory_per_function else 0
        functions_pct = (self.functions_used / plan.max_functions) * 100 if plan.max_functions else 0

        return {
            'cpu': min(cpu_pct, 100),
            'memory': min(memory_pct, 100),
            'functions': min(functions_pct, 100)
        }

    def __str__(self):
        return f"{self.user.email} - {self.tariff_plan.name}"

    class Meta:
        db_table = 'user_subscriptions'
        verbose_name = 'User Subscription'
        verbose_name_plural = 'User Subscriptions'
