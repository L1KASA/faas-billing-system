import logging
from decimal import Decimal
from django.utils import timezone
from django.core.cache import cache

from billing.billing_calculator import BillingCalculator
from faas_billing.config import config

logger = logging.getLogger(__name__)


class SimpleMetricsManager:
    """Упрощенный менеджер метрик"""

    @staticmethod
    def calculate_function_cost_now(function, user):
        """Расчет стоимости функции прямо сейчас"""
        try:
            calculator = BillingCalculator(user)

            # Используем текущие метрики функции или создаем базовые из конфига
            function_metrics = function.metrics.copy() if function.metrics else {}

            # Заполняем обязательные поля значениями из конфига если их нет
            default_metrics = config.get_default_function_metrics(function)
            for key, value in default_metrics.items():
                if key not in function_metrics:
                    function_metrics[key] = value

            # Расчет стоимости за разные периоды из конфига
            periods = config.get_periods()

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

            # Сохраняем в кэш с таймаутом из конфига
            cache_key = config.get_cache_key_function_cost(function.id, user.id)
            cache.set(cache_key, {
                'costs': {k: float(v['total_cost']) for k, v in costs.items()},
                'detailed_costs': costs,
                'metrics_used': function_metrics,
                'updated_at': timezone.now().isoformat()
            }, config.COST_CALCULATION_CACHE_TIMEOUT)

            return costs

        except Exception as e:
            logger.error(f"Error calculating cost for function {function.name}: {str(e)}")
            return None

    @staticmethod
    def get_cached_costs(function, user):
        """Получение кэшированных стоимостей"""
        cache_key = config.get_cache_key_function_cost(function.id, user.id)
        return cache.get(cache_key)

    @staticmethod
    def get_default_metrics_for_new_function(min_scale=1, memory_request=None):
        """
        Получить дефолтные метрики для новой функции
        """
        if memory_request is None:
            memory_request = config.DEFAULT_MEMORY_REQUEST_PER_POD

        return {
            'total_cpu_request': min_scale * config.DEFAULT_CPU_REQUEST_PER_POD,
            'total_memory_request': memory_request,
            'overall_efficiency': float(config.DEFAULT_EFFICIENCY_PERCENT),
            'cold_start_count': config.DEFAULT_COLD_START_COUNT,
            'pod_count': min_scale
        }

    @staticmethod
    def clear_cost_cache(function, user):
        """
        Очистить кэш стоимости для функции
        """
        cache_key = config.get_cache_key_function_cost(function.id, user.id)
        cache.delete(cache_key)
