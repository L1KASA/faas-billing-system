from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from decimal import Decimal

User = get_user_model()


class BillingConfig(models.Model):
    """Конфигурация тарифов и коэффициентов"""
    name = models.CharField(max_length=100, unique=True)

    # Базовые тарифы ($ за час)
    cpu_rate_per_hour = models.DecimalField(
        max_digits=10, decimal_places=6, default=Decimal('0.002'),
        validators=[MinValueValidator(Decimal('0.000001'))]
    )
    memory_rate_per_gb_hour = models.DecimalField(
        max_digits=10, decimal_places=6, default=Decimal('0.001'),
        validators=[MinValueValidator(Decimal('0.000001'))]
    )
    cold_start_penalty = models.DecimalField(
        max_digits=10, decimal_places=6, default=Decimal('0.005'),
        validators=[MinValueValidator(Decimal('0.000001'))]
    )

    # Коэффициенты
    platform_fee_rate = models.DecimalField(
        max_digits=5, decimal_places=3, default=Decimal('1.3'),
        validators=[MinValueValidator(Decimal('1.0'))]
    )
    min_efficiency_factor = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal('0.7'),
        validators=[MinValueValidator(Decimal('0.1'))]
    )
    max_efficiency_factor = models.DecimalField(
        max_digits=3, decimal_places=2, default=Decimal('1.3'),
        validators=[MinValueValidator(Decimal('1.0'))]
    )

    # Параметры для расчета стоимости холодных стартов
    cold_start_base_cost = models.DecimalField(
        max_digits=10, decimal_places=6, default=Decimal('0.002')
    )
    cold_start_queue_factor = models.DecimalField(
        max_digits=5, decimal_places=3, default=Decimal('1.5')
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} (CPU: ${self.cpu_rate_per_hour}/h)"


class BillingPeriod(models.Model):
    """Период биллинга"""

    class PeriodStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        CALCULATED = 'CALCULATED', 'Calculated'
        INVOICED = 'INVOICED', 'Invoiced'
        PAID = 'PAID', 'Paid'

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=PeriodStatus.choices, default=PeriodStatus.PENDING)

    total_cost = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0.0'))
    platform_fee = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0.0'))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'start_date', 'end_date']


class FunctionBillingRecord(models.Model):
    """Запись биллинга для конкретной функции за период"""
    billing_period = models.ForeignKey(BillingPeriod, on_delete=models.CASCADE, related_name='function_records')
    function = models.ForeignKey('functions.Function', on_delete=models.CASCADE)

    # Метрики за период
    cpu_hours = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0.0'))
    memory_gb_hours = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0.0'))
    cold_start_count = models.IntegerField(default=0)
    average_efficiency = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.0'))

    # Расчетные поля
    cpu_cost = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0.0'))
    memory_cost = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0.0'))
    cold_start_cost = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0.0'))
    efficiency_factor = models.DecimalField(max_digits=5, decimal_places=3, default=Decimal('1.0'))
    base_cost = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0.0'))
    final_cost = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0.0'))

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['function', 'billing_period']),
            models.Index(fields=['created_at']),
        ]
        unique_together = ['function', 'billing_period']


class HourlyFunctionMetrics(models.Model):
    """Почасовые метрики для агрегации"""
    function = models.ForeignKey('functions.Function', on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    cpu_seconds = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    memory_byte_seconds = models.DecimalField(max_digits=20, decimal_places=4, default=0)
    cold_start_count = models.IntegerField(default=0)
    pod_seconds = models.DecimalField(max_digits=15, decimal_places=4, default=0)
    raw_metrics = models.JSONField(default=dict)

    class Meta:
        indexes = [
            models.Index(fields=['function', 'timestamp']),
            models.Index(fields=['timestamp']),
        ]
        unique_together = ['function', 'timestamp']
