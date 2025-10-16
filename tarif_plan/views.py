from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from billing.billing_calculator import BillingCalculator
from tarif_plan.models import UserSubscription, TariffPlan
from tarif_plan.subscription_manager import SubscriptionManager


@login_required
def subscription_plans(request):
    """Страница с доступными тарифными планами"""
    plans = TariffPlan.objects.filter(is_active=True).order_by('monthly_price')

    # Текущая подписка пользователя
    current_subscription = SubscriptionManager.get_user_subscription(request.user)
    current_plan = current_subscription.tariff_plan if current_subscription else None

    # Проверка использования
    usage = {}
    limits_check = {}
    try:
        calculator = BillingCalculator(request.user)
        usage = calculator._get_current_usage()
        limits_check = calculator.check_plan_limits({})
    except Exception as e:
        usage = {'functions_count': 0, 'total_cpu': 0, 'total_memory': 0}
        limits_check = {'allowed': True, 'checks': {}, 'limits': {}, 'current_usage': usage}

    return render(request, 'billing/subscription_plans.html', {
        'plans': plans,
        'current_subscription': current_subscription,
        'current_plan': current_plan,
        'usage': usage,
        'limits_check': limits_check
    })


@login_required
@require_http_methods(["POST"])
def change_subscription(request):
    """Изменение подписки пользователя"""
    try:
        plan_tier = request.POST.get('plan_tier')
        print(f"DEBUG: plan_tier = {plan_tier}")

        new_plan = TariffPlan.objects.get(tier=plan_tier, is_active=True)
        print(f"DEBUG: new_plan = {new_plan.name}")

        success = SubscriptionManager.upgrade_plan(request.user, new_plan)
        print(f"DEBUG: upgrade_plan result = {success}")

        if success:
            return JsonResponse({
                'success': True,
                'message': f'Successfully upgraded to {new_plan.name}'
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Cannot upgrade to this plan'
            }, status=400)

    except TariffPlan.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Plan not found'
        }, status=404)
    except Exception as e:
        print(f"DEBUG: Exception = {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
def subscription_details(request):
    """Детали текущей подписки"""
    try:
        subscription = SubscriptionManager.get_user_subscription(request.user)
        if not subscription:
            return redirect('billing:subscription_plans')

        calculator = BillingCalculator(request.user)
        usage = calculator._get_current_usage()
        usage_percentage = subscription.usage_percentage

        # Расчет стоимости следующего платежа
        next_payment_date = subscription.end_date
        days_until_payment = (next_payment_date - timezone.now()).days if next_payment_date else 0

        return render(request, 'billing/subscription_details.html', {
            'subscription': subscription,
            'usage': usage,
            'usage_percentage': usage_percentage,
            'next_payment_date': next_payment_date,
            'days_until_payment': days_until_payment
        })

    except UserSubscription.DoesNotExist:
        return redirect('billing:subscription_plans')