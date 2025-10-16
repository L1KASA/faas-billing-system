from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from decimal import Decimal
import json
from faas_billing.config import config
from .billing_calculator import BillingCalculator
from .metrics_manager import SimpleMetricsManager
from .models import BillingPeriod
from functions.models import Function
from functions.knative_manager import KnativeManager


@login_required
def realtime_dashboard(request):
    """Дашборд с реальным временем"""
    functions = Function.objects.filter(user=request.user)

    # Получаем метрики и биллинг через SimpleMetricsManager
    realtime_data = {}
    for function in functions:
        costs = SimpleMetricsManager.calculate_function_cost_now(function, request.user)
        cached_costs = SimpleMetricsManager.get_cached_costs(function, request.user)

        # Получаем актуальные метрики из Knative
        knative_manager = KnativeManager()
        metrics_result = knative_manager.get_function_metrics(function.name)

        current_metrics = {}
        if metrics_result['success']:
            current_metrics = metrics_result['data']['summary']

        realtime_data[function.id] = {
            'function': function,
            'current_costs': costs,
            'cached_costs': cached_costs,
            'metrics': current_metrics,
            'knative_status': metrics_result['success']
        }

    return render(request, 'billing/realtime_dashboard.html', {
        'realtime_data': realtime_data,
        'update_interval': config.DASHBOARD_UPDATE_INTERVAL,
    })


@login_required
def billing_history(request):
    """История биллинга"""
    periods = BillingPeriod.objects.filter(user=request.user).order_by('-start_date')

    return render(request, 'billing/billing_history.html', {
        'periods': periods
    })


@login_required
def billing_dashboard(request):
    """Дашборд биллинга"""
    calculator = BillingCalculator(user=request.user)

    # Получаем текущий биллинг период или создаем новый
    today = timezone.now()
    first_day = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    try:
        current_period = BillingPeriod.objects.get(
            user=request.user,
            start_date__lte=today,
            end_date__gte=today
        )
    except BillingPeriod.DoesNotExist:
        # Создаем новый период если не найден
        current_period = BillingPeriod.objects.create(
            user=request.user,
            start_date=first_day,
            end_date=today,
            total_cost=Decimal('0.00'),
            platform_fee=Decimal('0.00'),
            status='active'
        )

    # Расчет стоимости для всех функций пользователя
    functions = Function.objects.filter(user=request.user)
    period_hours = Decimal(str((today - first_day).total_seconds() / 3600))  # часов в периоде

    function_costs = []
    total_cost = Decimal('0.00')

    for function in functions:
        # Получаем метрики функции из Knative
        function_metrics = get_function_metrics_from_knative(function)

        cost_breakdown = calculator.calculate_function_cost(
            function_metrics=function_metrics,
            period_hours=period_hours
        )

        function_costs.append({
            'function': function,
            'cost_breakdown': cost_breakdown
        })
        total_cost += cost_breakdown['total_cost']

    return render(request, 'users/dashboard.html', {
        'current_period': current_period,
        'function_costs': function_costs,
        'total_cost': total_cost,
        'trends': {},
        'recommendations': [],
    })


@login_required
@require_http_methods(["GET"])
def billing_api(request, period_id):
    """API для получения деталей биллинга"""
    try:
        period = BillingPeriod.objects.get(id=period_id, user=request.user)
        records = period.function_records.all()

        data = {
            'period': {
                'start_date': period.start_date.isoformat(),
                'end_date': period.end_date.isoformat(),
                'total_cost': float(period.total_cost),
                'platform_fee': float(period.platform_fee),
                'status': period.status,
            },
            'function_records': [
                {
                    'function_name': record.function.name,
                    'cpu_cost': float(record.cpu_cost),
                    'memory_cost': float(record.memory_cost),
                    'cold_start_cost': float(record.cold_start_cost),
                    'efficiency': float(record.average_efficiency),
                    'total_cost': float(record.final_cost),
                }
                for record in records
            ]
        }

        return JsonResponse(data)

    except BillingPeriod.DoesNotExist:
        return JsonResponse({'error': 'Billing period not found'}, status=404)


@login_required
@require_http_methods(["POST"])
def cost_estimation(request):
    """Оценка стоимости перед деплоем функции"""
    try:
        data = json.loads(request.body)

        # Параметры функции для оценки
        cpu_request = data.get('cpu_request', config.ESTIMATION_DEFAULT_CPU)  # millicores
        memory_request = data.get('memory_request', config.FALLBACK_MEMORY_PER_POD)  # bytes
        expected_cold_starts = data.get('expected_cold_starts', config.ESTIMATION_DEFAULT_COLD_STARTS)
        expected_efficiency = data.get('expected_efficiency', config.ESTIMATION_DEFAULT_EFFICIENCY)  # %

        calculator = BillingCalculator(user=request.user)

        estimation_metrics = {
            'total_cpu_request': cpu_request,
            'total_memory_request': memory_request,
            'cold_start_count': expected_cold_starts,
            'overall_efficiency': expected_efficiency
        }

        # Расчет за 30 дней
        period_hours = Decimal('720')  # 30 дней
        cost_breakdown = calculator.calculate_function_cost(
            function_metrics=estimation_metrics,
            period_hours=period_hours
        )

        return JsonResponse({
            'estimated_monthly_cost': float(cost_breakdown['total_cost']),
            'cost_breakdown': {
                'cpu': float(cost_breakdown['cpu_cost']),
                'memory': float(cost_breakdown['memory_cost']),
                'cold_starts': float(cost_breakdown['cold_start_cost']),
                'efficiency_factor': float(cost_breakdown['efficiency_factor']),
                'platform_fee': float(cost_breakdown['platform_fee']),
                'fixed_plan_cost': float(cost_breakdown['fixed_plan_cost']),
            }
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def plan_limits_check(request):
    """Проверка лимитов тарифного плана"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            calculator = BillingCalculator(user=request.user)
            limits_check = calculator.check_plan_limits(data)

            return JsonResponse(limits_check)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


@login_required
def function_cost_detail(request, function_id):
    """Детальная информация о стоимости функции"""
    try:
        function = Function.objects.get(id=function_id, user=request.user)
        calculator = BillingCalculator(user=request.user)

        # Расчет за разные периоды
        periods = config.get_ui_periods()

        function_metrics = get_function_metrics_from_knative(function)
        cost_breakdowns = {}

        for period_name, period_hours in periods.items():
            cost_breakdowns[period_name] = calculator.calculate_function_cost(
                function_metrics=function_metrics,
                period_hours=period_hours
            )

        return JsonResponse({
            'function_name': function.name,
            'metrics': function_metrics,
            'cost_breakdowns': cost_breakdowns
        })

    except Function.DoesNotExist:
        return JsonResponse({'error': 'Function not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def update_function_metrics(request, function_id):
    """Обновление метрик функции из Knative"""
    try:
        function = Function.objects.get(id=function_id, user=request.user)

        knative_manager = KnativeManager()
        metrics_result = knative_manager.get_function_metrics(function.name)

        if metrics_result['success']:
            metrics_data = metrics_result['data']['summary']

            # Обновляем метрики в модели Function
            if not function.metrics:
                function.metrics = {}

            # Обновляем накопленные метрики
            new_metrics = function.metrics.copy()
            for key in ['total_cpu_usage', 'total_memory_usage']:
                if key in function.metrics and key in metrics_data:
                    new_metrics[key] = function.metrics[key] + metrics_data[key]
                elif key in metrics_data:
                    new_metrics[key] = metrics_data[key]

            # Обновляем текущие метрики
            new_metrics.update({
                'total_cpu_request': metrics_data.get('total_cpu_request', 0),
                'total_memory_request': metrics_data.get('total_memory_request', 0),
                'pod_count': metrics_data.get('pod_count', 0),
                'total_pod_uptime_seconds': metrics_data.get('total_pod_uptime_seconds', 0),
                'max_cold_start_time_seconds': metrics_data.get('max_cold_start_time_seconds', 0),
                'cold_start_count': new_metrics.get('cold_start_count', 0) + 1  # увеличиваем счетчик холодных стартов
            })

            function.metrics = new_metrics
            function.save()

            return JsonResponse({
                'success': True,
                'metrics': new_metrics,
                'message': 'Metrics updated successfully'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': metrics_result['error']
            }, status=400)

    except Function.DoesNotExist:
        return JsonResponse({'error': 'Function not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# Вспомогательная функция для получения метрик функции из Knative
def get_function_metrics_from_knative(function):
    """
    Получение актуальных метрик функции из Knative
    """
    knative_manager = KnativeManager()
    metrics_result = knative_manager.get_function_metrics(function.name)

    if metrics_result['success']:
        knative_metrics = metrics_result['data']['summary']

        # Конвертируем nanocores в millicores для биллинга из конфига
        cpu_request_millicores = knative_metrics.get('total_cpu_request', 0) // config.NANOCORES_TO_MILLICORES
        cpu_usage_millicores = knative_metrics.get('total_cpu_usage', 0) // config.NANOCORES_TO_MILLICORES

        # Рассчитываем эффективность
        cpu_efficiency = 0
        if cpu_request_millicores > 0:
            cpu_efficiency = min((cpu_usage_millicores / cpu_request_millicores) * 100, 100)

        memory_efficiency = 0
        memory_request = knative_metrics.get('total_memory_request', 1)
        memory_usage = knative_metrics.get('total_memory_usage', 0)
        if memory_request > 0:
            memory_efficiency = min((memory_usage / memory_request) * 100, 100)

        overall_efficiency = (cpu_efficiency + memory_efficiency) / 2

        return {
            'total_cpu_request': cpu_request_millicores,
            'total_memory_request': knative_metrics.get('total_memory_request', 0),
            'cold_start_count': function.metrics.get('cold_start_count', 0) if function.metrics else 0,
            'overall_efficiency': overall_efficiency,
            'pod_count': knative_metrics.get('pod_count', 0),
            'total_pod_uptime_seconds': knative_metrics.get('total_pod_uptime_seconds', 0),
        }

    # Возвращаем базовые метрики из конфига если не удалось получить из Knative
    return config.get_fallback_metrics(function)
