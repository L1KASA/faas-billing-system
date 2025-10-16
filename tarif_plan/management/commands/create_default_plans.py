from django.core.management.base import BaseCommand
from tarif_plan.models import TariffPlan
from decimal import Decimal

class Command(BaseCommand):
    help = 'Create default tariff plans'

    def handle(self, *args, **options):
        plans_data = [
            {
                'name': 'Starter',
                'tier': TariffPlan.PlanTier.STARTER,
                'description': 'Perfect for getting started',
                'monthly_price': Decimal('0.00'),
                'max_functions': 5,
                'max_cpu_per_function': 1000,
                'max_memory_per_function': 1073741824,  # 1GB
                'max_scale': 5,
            },
            {
                'name': 'Professional',
                'tier': TariffPlan.PlanTier.PROFESSIONAL,
                'description': 'For growing businesses',
                'monthly_price': Decimal('29.99'),
                'max_functions': 20,
                'max_cpu_per_function': 2000,
                'max_memory_per_function': 2147483648,  # 2GB
                'max_scale': 10,
                'includes_support': True,
            },
            {
                'name': 'Enterprise',
                'tier': TariffPlan.PlanTier.ENTERPRISE,
                'description': 'For large scale applications',
                'monthly_price': Decimal('99.99'),
                'max_functions': 100,
                'max_cpu_per_function': 4000,
                'max_memory_per_function': 4294967296,  # 4GB
                'max_scale': 20,
                'includes_support': True,
                'includes_analytics': True,
                'includes_sla': True,
            }
        ]

        for plan_data in plans_data:
            plan, created = TariffPlan.objects.get_or_create(
                tier=plan_data['tier'],
                defaults=plan_data
            )
            if created:
                self.stdout.write(f"Created {plan.name} plan")
            else:
                self.stdout.write(f"{plan.name} plan already exists")

        self.stdout.write(self.style.SUCCESS('Default plans created successfully'))
