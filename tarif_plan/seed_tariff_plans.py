from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from tarif_plan.models import TariffPlan, UserSubscription
from django.utils import timezone
from datetime import timedelta

User = get_user_model()


class Command(BaseCommand):
    help = 'Create default subscriptions for all users without subscription'

    def handle(self, *args, **options):
        try:
            # Получаем стартовый тарифный план
            starter_plan = TariffPlan.objects.get(tier=TariffPlan.PlanTier.STARTER)
        except TariffPlan.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('Starter tariff plan not found. Run seed_tariff_plans first.')
            )
            return

        users_without_subscription = User.objects.filter(
            usersubscription__isnull=True
        )

        created_count = 0

        for user in users_without_subscription:
            # Создаем подписку по умолчанию
            UserSubscription.objects.create(
                user=user,
                tariff_plan=starter_plan,
                status=UserSubscription.SubscriptionStatus.ACTIVE,
                end_date=timezone.now() + timedelta(days=30),
                auto_renew=True
            )
            created_count += 1

        if created_count > 0:
            self.stdout.write(
                self.style.SUCCESS(f'Created {created_count} default subscriptions')
            )
        else:
            self.stdout.write(
                self.style.WARNING('No users without subscription found')
            )