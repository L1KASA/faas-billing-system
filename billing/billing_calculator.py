from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional

from billing.models import BillingConfig
from tarif_plan.models import TariffPlan, UserSubscription
from users.models import User


class MetricsCalculator:
    """Калькулятор метрик эффективности"""

    @staticmethod
    def calculate_efficiency_metrics(function):
        """
        Расчет ключевых метрик эффективности на основе данных из Function.metrics
        """
        metrics = function.metrics

        # 1. ЭФФЕКТИВНОСТЬ ИСПОЛЬЗОВАНИЯ РЕСУРСОВ
        cpu_efficiency = MetricsCalculator._calculate_cpu_efficiency(
            metrics.get('total_cpu_usage', 0),
            metrics.get('total_cpu_request', 1)
        )

        memory_efficiency = MetricsCalculator._calculate_memory_efficiency(
            metrics.get('total_memory_usage', 0),
            metrics.get('total_memory_request', 1)
        )

        # 2. ОБЩАЯ ЭФФЕКТИВНОСТЬ (средневзвешенная)
        overall_efficiency = (cpu_efficiency + memory_efficiency) / 2

        # 3. ЭКОНОМИЯ ЗАТРАТ (условная формула)
        cost_saving = MetricsCalculator._calculate_cost_saving(
            cpu_efficiency,
            memory_efficiency,
            metrics.get('pod_count', 0)
        )

        return {
            'cpu_efficiency': round(cpu_efficiency, 2),
            'memory_efficiency': round(memory_efficiency, 2),
            'overall_efficiency': round(overall_efficiency, 2),
            'cost_saving_percent': round(cost_saving, 2),
            'performance_score': MetricsCalculator._calculate_performance_score(metrics)
        }

    @staticmethod
    def _calculate_cpu_efficiency(actual_usage, requested):
        """
        Формула эффективности использования CPU:
        Эффективность = (Фактическое использование / Запрошенное) × 100%
        """
        if requested == 0:
            return 0
        return min((actual_usage / requested) * 100, 100)

    @staticmethod
    def _calculate_memory_efficiency(actual_usage, requested):
        """
        Формула эффективности использования памяти:
        Эффективность = (Фактическое использование / Запрошенное) × 100%
        """
        if requested == 0:
            return 0
        return min((actual_usage / requested) * 100, 100)

    @staticmethod
    def _calculate_cost_saving(cpu_eff, memory_eff, pod_count):
        """
        Условная формула экономии затрат:
        Экономия = (100% - Средняя эффективность) × Коэффициент масштабирования
        """
        avg_efficiency = (cpu_eff + memory_eff) / 2
        scale_factor = min(pod_count / 10, 1)
        return (100 - avg_efficiency) * scale_factor

    @staticmethod
    def _calculate_performance_score(metrics):
        """
        Оценка производительности на основе времени работы и холодного старта
        """
        uptime = metrics.get('total_pod_uptime_seconds', 0)
        cold_start = metrics.get('max_cold_start_time_seconds', 0)

        uptime_score = min(uptime / 3600, 100)
        cold_start_penalty = min(cold_start * 10, 50)

        return max(uptime_score - cold_start_penalty, 0)


class BillingCalculator:
    """Калькулятор стоимости с учетом тарифных планов"""

    def __init__(self, user: User = None, config: BillingConfig = None):
        self.user = user
        self.config = config or BillingConfig.objects.first()

        # Получаем тарифный план пользователя
        self.tariff_plan = self._get_user_tariff_plan()

        if not self.config:
            self.config = BillingConfig.objects.create(
                name="Default Billing Config",
                # базовые значения...
            )

    def _get_user_tariff_plan(self) -> Optional[TariffPlan]:
        """Получение текущего тарифного плана пользователя"""
        try:
            if not self.user:
                # Возвращаем дефолтный план если пользователь не указан
                return TariffPlan.objects.filter(
                    tier=TariffPlan.PlanTier.STARTER,
                    is_active=True
                ).first()

            # Получаем подписку пользователя
            subscription = UserSubscription.objects.filter(
                user=self.user,
                status=UserSubscription.SubscriptionStatus.ACTIVE
            ).select_related('tariff_plan').first()

            if subscription:
                return subscription.tariff_plan

            # Возвращаем дефолтный план если подписки нет
            default_plan = TariffPlan.objects.filter(
                tier=TariffPlan.PlanTier.STARTER,
                is_active=True
            ).first()

            if not default_plan:
                default_plan = TariffPlan.objects.create(
                    name="Starter Plan",
                    tier=TariffPlan.PlanTier.STARTER,
                    description="Default starter plan",
                    is_active=True,
                    monthly_price=Decimal('0.00')
                )
            return default_plan

        except Exception as e:
            print(f"Error getting tariff plan: {e}")
            return None

    def calculate_function_cost(
        self,
        function_metrics: Dict,
        period_hours: Decimal,
        cluster_metrics: Optional[Dict] = None
    ) -> Dict[str, Decimal]:
        """
        Расчет стоимости для одной функции с учетом тарифного плана
        """
        if not self.tariff_plan:
            self.tariff_plan = self._get_user_tariff_plan()

        # Если тарифный план все еще None, используем значения по умолчанию
        if not self.tariff_plan:
            cpu_rate = Decimal('0.002')
            memory_rate = Decimal('0.001')
            cold_start_penalty = Decimal('0.005')
            platform_fee_rate = Decimal('1.3')
            min_efficiency = Decimal('0.7')
            max_efficiency = Decimal('1.3')
        else:
            # Используем тарифы из плана пользователя
            cpu_rate = getattr(self.tariff_plan, 'cpu_rate_per_hour', Decimal('0.002'))
            memory_rate = getattr(self.tariff_plan, 'memory_rate_per_gb_hour', Decimal('0.001'))
            cold_start_penalty = getattr(self.tariff_plan, 'cold_start_penalty', Decimal('0.005'))
            platform_fee_rate = getattr(self.tariff_plan, 'platform_fee_rate', Decimal('1.3'))
            min_efficiency = getattr(self.tariff_plan, 'min_efficiency_factor', Decimal('0.7'))
            max_efficiency = getattr(self.tariff_plan, 'max_efficiency_factor', Decimal('1.3'))

        # 1. БАЗОВАЯ СТОИМОСТЬ РЕСУРСОВ
        cpu_hours = Decimal(str(function_metrics.get('total_cpu_request', 0))) / Decimal('1000') * period_hours
        memory_gb_hours = (
            Decimal(str(function_metrics.get('total_memory_request', 0))) /
            Decimal(str(1024 ** 3)) * period_hours
        )

        cpu_cost = cpu_hours * cpu_rate
        memory_cost = memory_gb_hours * memory_rate

        # 2. СТОИМОСТЬ ХОЛОДНЫХ СТАРТОВ
        cold_start_count = function_metrics.get('cold_start_count', 0)
        cold_start_cost = self.calculate_cold_start_cost(
            cold_start_count, cluster_metrics, cold_start_penalty
        )

        # 3. КОЭФФИЦИЕНТ ЭФФЕКТИВНОСТИ (с ограничениями из тарифа)
        efficiency = Decimal(str(function_metrics.get('overall_efficiency', 100)))
        efficiency_factor = self.calculate_efficiency_factor(efficiency, min_efficiency, max_efficiency)

        # 4. БАЗОВАЯ СТОИМОСТЬ (до применения платформенной наценки)
        base_cost = (cpu_cost + memory_cost + cold_start_cost) * efficiency_factor

        # 5. ФИНАЛЬНАЯ СТОИМОСТЬ (с платформенной наценкой из тарифа)
        final_cost = base_cost * platform_fee_rate

        # 6. ДОБАВЛЯЕМ ФИКСИРОВАННУЮ СТОИМОСТЬ ПЛАНА (пропорционально периоду)
        fixed_cost = self._calculate_fixed_plan_cost(period_hours)

        total_cost = final_cost + fixed_cost

        return {
            'cpu_hours': cpu_hours.quantize(Decimal('0.0001')),
            'memory_gb_hours': memory_gb_hours.quantize(Decimal('0.0001')),
            'cold_start_count': cold_start_count,
            'average_efficiency': efficiency.quantize(Decimal('0.01')),

            'cpu_cost': cpu_cost.quantize(Decimal('0.0001')),
            'memory_cost': memory_cost.quantize(Decimal('0.0001')),
            'cold_start_cost': cold_start_cost.quantize(Decimal('0.0001')),
            'efficiency_factor': efficiency_factor,
            'base_cost': base_cost.quantize(Decimal('0.0001')),
            'final_cost': final_cost.quantize(Decimal('0.0001')),
            'fixed_plan_cost': fixed_cost.quantize(Decimal('0.0001')),
            'total_cost': total_cost.quantize(Decimal('0.0001')),
            'platform_fee': (final_cost - base_cost).quantize(Decimal('0.0001'))
        }

    def calculate_cold_start_cost(
        self,
        cold_start_count: int,
        cluster_metrics: Optional[Dict] = None,
        cold_start_penalty: Decimal = Decimal('0.005')
    ) -> Decimal:
        """
        Расчет стоимости холодных стартов функции

        Args:
            cold_start_count: количество холодных стартов
            cluster_metrics: метрики кластера (опционально)
            cold_start_penalty: стоимость одного холодного старта

        Returns:
            Стоимость всех холодных стартов функции
        """
        if cold_start_count <= 0:
            return Decimal('0')

        # Базовая стоимость = количество холодных стартов × штраф за старт
        base_cost = Decimal(cold_start_count) * cold_start_penalty

        # Если есть метрики кластера, можно учесть дополнительные факторы
        if cluster_metrics:
            # Пример: учет загрузки кластера при холодных стартах
            cluster_load = Decimal(str(cluster_metrics.get('average_load_percent', 50)))

            # Коэффициент влияния загрузки кластера (чем выше загрузка, тем дороже холодные старты)
            load_factor = Decimal('1.0') + (cluster_load - Decimal('50')) / Decimal('100')

            # Ограничиваем коэффициент разумными пределами
            load_factor = max(Decimal('0.8'), min(Decimal('1.5'), load_factor))

            base_cost = base_cost * load_factor

        return base_cost

    def calculate_efficiency_factor(
        self,
        efficiency: Decimal,
        min_efficiency: Decimal,
        max_efficiency: Decimal
    ) -> Decimal:
        """
        Расчет коэффициента эффективности с ограничениями из тарифа
        """
        if efficiency <= Decimal('0'):
            return max_efficiency

        raw_factor = Decimal('100') / efficiency

        bounded_factor = max(
            min_efficiency,
            min(max_efficiency, raw_factor)
        )

        return bounded_factor.quantize(Decimal('0.001'), rounding=ROUND_HALF_UP)

    def _calculate_fixed_plan_cost(self, period_hours: Decimal) -> Decimal:
        """
        Расчет фиксированной стоимости тарифного плана за период
        """
        if not self.tariff_plan:
            return Decimal('0')

        monthly_price = self.tariff_plan.monthly_price
        if monthly_price == Decimal('0'):
            return Decimal('0')

        # Пересчитываем месячную цену в стоимость за период
        hours_in_month = Decimal('730')  # ~30.42 дней
        fixed_cost = (monthly_price / hours_in_month) * period_hours

        return fixed_cost.quantize(Decimal('0.0001'))

    def check_plan_limits(self, function_data: Dict) -> Dict[str, bool]:
        """
        Проверка соответствия функции лимитам тарифного плана
        """
        if not self.tariff_plan:
            self.tariff_plan = self._get_user_tariff_plan()

        # Если тарифного плана нет, используем значения по умолчанию
        if not self.tariff_plan:
            plan_limits = {
                'max_functions': 10,
                'max_cpu_per_function': 2000,
                'max_memory_per_function': 2147483648,
                'max_scale': 10,
            }
        else:
            plan_limits = {
                'max_functions': getattr(self.tariff_plan, 'max_functions', 10),
                'max_cpu_per_function': getattr(self.tariff_plan, 'max_cpu_per_function', 2000),
                'max_memory_per_function': getattr(self.tariff_plan, 'max_memory_per_function', 2147483648),
                'max_scale': getattr(self.tariff_plan, 'max_scale', 10),
            }

        current_usage = self._get_current_usage()

        # Проверяем лимиты
        checks = {
            'functions_limit': current_usage['functions_count'] < plan_limits['max_functions'],
            'cpu_limit': function_data.get('cpu_request', 0) <= plan_limits['max_cpu_per_function'],
            'memory_limit': function_data.get('memory_request', 0) <= plan_limits['max_memory_per_function'],
            'scale_limit': function_data.get('max_scale', 0) <= plan_limits['max_scale'],
        }

        return {
            'allowed': all(checks.values()),
            'checks': checks,
            'limits': plan_limits,
            'current_usage': current_usage
        }

    def _get_current_usage(self) -> Dict:
        """Текущее использование ресурсов пользователем"""
        if not self.user:
            return {'functions_count': 0}

        # Предполагаем, что у пользователя есть связь с функциями через related_name
        # Если у вас другая структура, нужно адаптировать этот код
        try:
            functions_count = self.user.functions.count() if hasattr(self.user, 'functions') else 0
        except Exception:
            functions_count = 0

        # Расчет общего CPU и памяти
        total_cpu = 0
        total_memory = 0

        # Если есть доступ к функциям пользователя, рассчитываем использование
        if hasattr(self.user, 'functions') and hasattr(self.user.functions, 'all'):
            for function in self.user.functions.all():
                # Адаптируйте эти расчеты под вашу модель Function
                total_cpu += getattr(function, 'min_scale', 1) * 1000
                total_memory += getattr(function, 'min_scale', 1) * 536870912

        return {
            'functions_count': functions_count,
            'total_cpu': total_cpu,
            'total_memory': total_memory
        }