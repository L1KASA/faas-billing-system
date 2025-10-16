from datetime import timedelta
from decimal import Decimal

from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db import transaction

from tarif_plan.models import TariffPlan, UserSubscription
from users.models import User


class SubscriptionManager:
    """Управление подписками пользователей"""

    @staticmethod
    def get_user_subscription(user: User):
        """Получение подписки пользователя"""
        try:
            return UserSubscription.objects.get(user=user)
        except UserSubscription.DoesNotExist:
            return None

    @staticmethod
    def get_active_subscription(user: User):
        """Получение активной подписки пользователя"""
        try:
            subscription = UserSubscription.objects.get(
                user=user,
                status=UserSubscription.SubscriptionStatus.ACTIVE
            )
            return subscription
        except UserSubscription.DoesNotExist:
            return None

    @staticmethod
    def create_subscription(user: User, tariff_plan: TariffPlan) -> UserSubscription:
        """Создание новой подписки"""
        with transaction.atomic():
            # Получаем или создаем подписку
            subscription, created = UserSubscription.objects.get_or_create(
                user=user,
                defaults={
                    'tariff_plan': tariff_plan,
                    'status': UserSubscription.SubscriptionStatus.ACTIVE,
                    'start_date': timezone.now(),
                    'end_date': timezone.now() + timedelta(days=30),
                    'auto_renew': True
                }
            )

            # Если подписка уже существует, обновляем ее
            if not created:
                subscription.tariff_plan = tariff_plan
                subscription.status = UserSubscription.SubscriptionStatus.ACTIVE
                subscription.start_date = timezone.now()
                subscription.end_date = timezone.now() + timedelta(days=30)
                subscription.auto_renew = True
                subscription.save()

        SubscriptionManager._send_subscription_email(user, tariff_plan, 'created')
        return subscription

    @staticmethod
    def cancel_subscription(user: User, immediate: bool = True) -> bool:
        """Отмена подписки"""
        try:
            subscription = SubscriptionManager.get_active_subscription(user)
            if not subscription:
                return False

            if immediate:
                subscription.status = UserSubscription.SubscriptionStatus.CANCELLED
                subscription.auto_renew = False
                subscription.save()

                # Отправляем email об отмене
                SubscriptionManager._send_subscription_email(
                    user, subscription.tariff_plan, 'cancelled'
                )
            else:
                # Просто выключаем автопродление
                subscription.auto_renew = False
                subscription.save()

            return True

        except UserSubscription.DoesNotExist:
            return False

    @staticmethod
    def upgrade_plan(user: User, new_tariff_plan: TariffPlan) -> bool:
        """Обновление тарифного плана"""
        try:
            current_subscription = SubscriptionManager.get_active_subscription(user)

            # Если у пользователя нет активной подписки, просто создаем новую
            if not current_subscription:
                SubscriptionManager.create_subscription(user, new_tariff_plan)
                return True

            # Проверяем, можно ли обновить (только если есть текущая подписка)
            if not SubscriptionManager._can_upgrade(current_subscription.tariff_plan, new_tariff_plan):
                return False

            # ОБНОВЛЯЕМ существующую подписку вместо создания новой
            current_subscription.tariff_plan = new_tariff_plan
            current_subscription.start_date = timezone.now()
            current_subscription.end_date = timezone.now() + timedelta(days=30)
            current_subscription.save()

            # Рассчитываем пропорциональную стоимость
            refund_amount = SubscriptionManager._calculate_prorated_refund(
                current_subscription, new_tariff_plan
            )

            if refund_amount > 0:
                # Возврат средств или кредит на счет
                SubscriptionManager._process_refund(user, refund_amount)

            SubscriptionManager._send_subscription_email(user, new_tariff_plan, 'upgraded')
            return True

        except Exception as e:
            print(f"Error in upgrade_plan: {str(e)}")
            return False

    @staticmethod
    def _can_upgrade(current_plan: TariffPlan, new_plan: TariffPlan) -> bool:
        """Проверка возможности обновления плана"""
        plan_order = {
            TariffPlan.PlanTier.STARTER: 1,
            TariffPlan.PlanTier.PROFESSIONAL: 2,
            TariffPlan.PlanTier.ENTERPRISE: 3
        }

        current_level = plan_order.get(current_plan.tier, 0)
        new_level = plan_order.get(new_plan.tier, 0)

        return new_level > current_level

    @staticmethod
    def _calculate_prorated_refund(
        current_subscription: UserSubscription,
        new_plan: TariffPlan
    ) -> Decimal:
        """Расчет пропорционального возврата средств"""
        days_used = (timezone.now() - current_subscription.start_date).days
        days_in_period = 30

        used_ratio = Decimal(str(days_used)) / Decimal(str(days_in_period))
        amount_used = current_subscription.tariff_plan.monthly_price * used_ratio

        return current_subscription.tariff_plan.monthly_price - amount_used

    @staticmethod
    def _send_subscription_email(user: User, plan: TariffPlan, action: str):
        """Отправка email уведомления о подписке"""
        subject_map = {
            'created': f'Subscription Confirmed - {plan.name}',
            'cancelled': f'Subscription Cancelled - {plan.name}',
            'upgraded': f'Subscription Upgraded - {plan.name}',
            'renewed': f'Subscription Renewed - {plan.name}',
            'expired': f'Subscription Expired - {plan.name}'
        }

        subject = subject_map.get(action, 'Subscription Update')

        send_mail(
            subject=subject,
            message=f'Your subscription has been {action}. Plan: {plan.name}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=True
        )

    @staticmethod
    def _process_payment(user: User, plan: TariffPlan):
        """Обработка платежа (заглушка для интеграции с платежной системой)"""
        pass

    @staticmethod
    def _process_refund(user: User, amount: Decimal):
        """Обработка возврата средств (заглушка)"""
        pass

    @staticmethod
    def check_expired_subscriptions():
        """Проверка и обработка истекших подписок"""
        expired_subscriptions = UserSubscription.objects.filter(
            end_date__lt=timezone.now(),
            status=UserSubscription.SubscriptionStatus.ACTIVE
        )

        for subscription in expired_subscriptions:
            if subscription.auto_renew:
                # Автопродление
                new_end_date = timezone.now() + timedelta(days=30)
                subscription.end_date = new_end_date
                subscription.save()

                SubscriptionManager._process_payment(subscription.user, subscription.tariff_plan)
                SubscriptionManager._send_subscription_email(
                    subscription.user, subscription.tariff_plan, 'renewed'
                )
            else:
                # Отключаем подписку
                subscription.status = UserSubscription.SubscriptionStatus.EXPIRED
                subscription.save()

                SubscriptionManager._send_subscription_email(
                    subscription.user, subscription.tariff_plan, 'expired'
                )
