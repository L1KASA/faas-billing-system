import logging
from decimal import Decimal
from django.utils import timezone
from django.core.cache import cache

from billing.billing_calculator import BillingCalculator

logger = logging.getLogger(__name__)


class SimpleMetricsManager:
    """Упрощенный менеджер метрик"""

    @staticmethod
    def calculate_function_cost_now(function, user):
        """Расчет стоимости функции прямо сейчас"""
        try:
            calculator = BillingCalculator(user)

            # Используем текущие метрики функции или создаем базовые
            function_metrics = function.metrics.copy() if function.metrics else {}

            # Заполняем обязательные поля если их нет
            if 'total_cpu_request' not in function_metrics:
                function_metrics['total_cpu_request'] = function.min_scale * 1000  # millicores

            if 'total_memory_request' not in function_metrics:
                function_metrics['total_memory_request'] = getattr(function, 'memory_request', 536870912)

            if 'overall_efficiency' not in function_metrics:
                function_metrics['overall_efficiency'] = 80  # дефолтная эффективность

            if 'cold_start_count' not in function_metrics:
                function_metrics['cold_start_count'] = 0

            # Расчет стоимости за разные периоды
            periods = {
                'minute': Decimal('0.01667'),  # 1 минута в часах
                'hour': Decimal('1'),
                'day': Decimal('24'),
                'month': Decimal('720')  # 30 дней
            }

            costs = {}
            for period_name, period_hours in periods.items():
                cost_breakdown = calculator.calculate_function_cost(
                    function_metrics,
                    period_hours
                )
                costs[period_name] = {
                    'total_cost': cost_breakdown['total_cost'],
                    'cpu_cost': cost_breakdown['cpu_cost'],
                    'memory_cost': cost_breakdown['memory_cost'],
                    'cold_start_cost': cost_breakdown['cold_start_cost'],
                    'platform_fee': cost_breakdown['platform_fee']
                }

            # Сохраняем в кэш на 2 минуты
            cache_key = f"function_cost_{function.id}_{user.id}"
            cache.set(cache_key, {
                'costs': {k: float(v['total_cost']) for k, v in costs.items()},
                'detailed_costs': costs,
                'metrics_used': function_metrics,
                'updated_at': timezone.now().isoformat()
            }, 120)  # 2 минуты

            return costs

        except Exception as e:
            logger.error(f"Error calculating cost for function {function.name}: {str(e)}")
            return None

    @staticmethod
    def get_cached_costs(function, user):
        """Получение кэшированных стоимостей"""
        cache_key = f"function_cost_{function.id}_{user.id}"
        return cache.get(cache_key)
