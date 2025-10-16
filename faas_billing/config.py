"""
Конфигурация приложения в виде класса
"""

from decimal import Decimal
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # =============================================================================
    # ЦЕНЫ РЕСУРСОВ
    # =============================================================================
    CPU_RATE = Decimal(os.getenv('CPU_RATE', '0.002'))
    MEMORY_RATE = Decimal(os.getenv('MEMORY_RATE', '0.001'))
    COLD_START_RATE = Decimal(os.getenv('COLD_START_RATE', '0.005'))
    PLATFORM_FEE = Decimal(os.getenv('PLATFORM_FEE', '1.3'))

    # =============================================================================
    # КОЭФФИЦИЕНТЫ ЭФФЕКТИВНОСТИ
    # =============================================================================
    EFFICIENCY_MIN = Decimal(os.getenv('EFFICIENCY_MIN', '0.7'))
    EFFICIENCY_MAX = Decimal(os.getenv('EFFICIENCY_MAX', '1.3'))

    # =============================================================================
    # КОЭФФИЦИЕНТЫ ЗАГРУЗКИ
    # =============================================================================
    CLUSTER_LOAD_MIN = Decimal(os.getenv('CLUSTER_LOAD_MIN', '0.8'))
    CLUSTER_LOAD_MAX = Decimal(os.getenv('CLUSTER_LOAD_MAX', '1.5'))
    CLUSTER_LOAD_BASE = Decimal(os.getenv('CLUSTER_LOAD_BASE', '50'))

    # =============================================================================
    # ЛИМИТЫ ТАРИФОВ
    # =============================================================================
    PLAN_LIMITS_STARTER_MAX_FUNCTIONS = 5
    PLAN_LIMITS_STARTER_MAX_CPU = 1000
    PLAN_LIMITS_STARTER_MAX_MEMORY = 1073741824
    PLAN_LIMITS_STARTER_MAX_SCALE = 5

    PLAN_LIMITS_PROFESSIONAL_MAX_FUNCTIONS = 20
    PLAN_LIMITS_PROFESSIONAL_MAX_CPU = 2000
    PLAN_LIMITS_PROFESSIONAL_MAX_MEMORY = 2147483648
    PLAN_LIMITS_PROFESSIONAL_MAX_SCALE = 10

    PLAN_LIMITS_ENTERPRISE_MAX_FUNCTIONS = 100
    PLAN_LIMITS_ENTERPRISE_MAX_CPU = 4000
    PLAN_LIMITS_ENTERPRISE_MAX_MEMORY = 4294967296
    PLAN_LIMITS_ENTERPRISE_MAX_SCALE = 20

    # =============================================================================
    # РАСЧЕТНЫЕ КОНСТАНТЫ
    # =============================================================================
    HOURS_IN_MONTH = Decimal('730')
    MILLICORES_PER_CORE = Decimal('1000')
    BYTES_PER_GB = Decimal('1073741824')
    SECONDS_PER_HOUR = Decimal('3600')

    # =============================================================================
    # ПЕРИОДЫ РАСЧЕТА
    # =============================================================================
    PERIOD_MINUTE = Decimal('0.01667')
    PERIOD_HOUR = Decimal('1')
    PERIOD_DAY = Decimal('24')
    PERIOD_MONTH = Decimal('720')

    # =============================================================================
    # КЭШ
    # =============================================================================
    CACHE_TIMEOUT = int(os.getenv('CACHE_TIMEOUT', '120'))

    # =============================================================================
    # НАСТРОЙКИ ЭЛЕКТРОННОЙ ПОЧТЫ
    # =============================================================================
    EMAIL_VERIFICATION_TIMEOUT = int(os.getenv('EMAIL_VERIFICATION_TIMEOUT', '900'))
    PASSWORD_RECOVERY_CODE_LENGTH = int(os.getenv('PASSWORD_RECOVERY_CODE_LENGTH', '6'))
    PASSWORD_RECOVERY_TIMEOUT = int(os.getenv('PASSWORD_RECOVERY_TIMEOUT', '900'))

    # Тексты писем
    EMAIL_SUBJECT_VERIFICATION = os.getenv('EMAIL_SUBJECT_VERIFICATION', 'Verify your email address')
    EMAIL_SUBJECT_WELCOME = os.getenv('EMAIL_SUBJECT_WELCOME', 'Welcome to Our Service!')
    EMAIL_SUBJECT_RECOVERY = os.getenv('EMAIL_SUBJECT_RECOVERY', 'Password Recovery Code')

    # Шаблоны писем
    EMAIL_TEMPLATE_VERIFICATION = os.getenv('EMAIL_TEMPLATE_VERIFICATION', 'users/email/verification_email.html')
    EMAIL_TEMPLATE_WELCOME = os.getenv('EMAIL_TEMPLATE_WELCOME', 'users/email/welcome_email.html')
    EMAIL_TEMPLATE_RECOVERY = os.getenv('EMAIL_TEMPLATE_RECOVERY', 'users/email/recovery_code.html')

    # =============================================================================
    # НАСТРОЙКИ МЕТРИК И КЭШИРОВАНИЯ
    # =============================================================================
    METRICS_CACHE_TIMEOUT = int(os.getenv('METRICS_CACHE_TIMEOUT', '120'))
    COST_CALCULATION_CACHE_TIMEOUT = int(os.getenv('COST_CALCULATION_CACHE_TIMEOUT', '120'))

    # Дефолтные значения метрик
    DEFAULT_CPU_REQUEST_PER_POD = int(os.getenv('DEFAULT_CPU_REQUEST_PER_POD', '1000'))
    DEFAULT_MEMORY_REQUEST_PER_POD = int(os.getenv('DEFAULT_MEMORY_REQUEST_PER_POD', '536870912'))
    DEFAULT_EFFICIENCY_PERCENT = Decimal(os.getenv('DEFAULT_EFFICIENCY_PERCENT', '80'))
    DEFAULT_COLD_START_COUNT = int(os.getenv('DEFAULT_COLD_START_COUNT', '0'))

    # Ключи кэша
    CACHE_KEY_FUNCTION_COST = "function_cost_{function_id}_{user_id}"
    CACHE_KEY_METRICS = "metrics_{function_id}"

    # =============================================================================
    # НАСТРОЙКИ KUBERNETES И KNATIVE
    # =============================================================================
    KUBERNETES_NAMESPACE = os.getenv('KUBERNETES_NAMESPACE', 'default')

    # Knative API configuration
    KNATIVE_GROUP = "serving.knative.dev"
    KNATIVE_VERSION = "v1"
    KNATIVE_PLURAL = "services"

    # Metrics API configuration
    METRICS_GROUP = "metrics.k8s.io"
    METRICS_VERSION = "v1beta1"
    METRICS_PLURAL = "pods"

    # Дефолтные значения для деплоя функций
    DEFAULT_CONTAINER_MEMORY_REQUEST = os.getenv('DEFAULT_CONTAINER_MEMORY_REQUEST', '128Mi')
    DEFAULT_CONTAINER_CPU_REQUEST = os.getenv('DEFAULT_CONTAINER_CPU_REQUEST', '100m')
    DEFAULT_MIN_SCALE = int(os.getenv('DEFAULT_MIN_SCALE', '0'))
    DEFAULT_MAX_SCALE = int(os.getenv('DEFAULT_MAX_SCALE', '5'))

    # Аннотации для autoscaling
    AUTOSCALING_MIN_ANNOTATION = "autoscaling.knative.dev/minScale"
    AUTOSCALING_MAX_ANNOTATION = "autoscaling.knative.dev/maxScale"

    # Label selectors
    SERVICE_LABEL_SELECTOR = "serving.knative.dev/service={service_name}"

    # Коэффициенты конвертации ресурсов
    CPU_CONVERSION_FACTORS = {
        'n': 1,
        'u': 1000,
        'm': 1000000,
        'default': 1000000000
    }

    MEMORY_CONVERSION_FACTORS = {
        'Ki': 1024,
        'Mi': 1024 * 1024,
        'Gi': 1024 * 1024 * 1024,
        'K': 1000,
        'M': 1000 * 1000,
        'G': 1000 * 1000 * 1000,
        'default': 1
    }

    # =============================================================================
    # МЕТОДЫ ДЛЯ РАБОТЫ С КОНФИГОМ
    # =============================================================================

    @classmethod
    def get_periods(cls) -> dict:
        """Получить все периоды расчета стоимости"""
        return {
            'minute': cls.PERIOD_MINUTE,
            'hour': cls.PERIOD_HOUR,
            'day': cls.PERIOD_DAY,
            'month': cls.PERIOD_MONTH
        }

    @classmethod
    def get_cache_key_function_cost(cls, function_id, user_id) -> str:
        """Получить ключ кэша для стоимости функции"""
        return cls.CACHE_KEY_FUNCTION_COST.format(
            function_id=function_id,
            user_id=user_id
        )

    @classmethod
    def get_default_function_metrics(cls, function) -> dict:
        """Получить дефолтные метрики для функции"""
        return {
            'total_cpu_request': function.min_scale * cls.DEFAULT_CPU_REQUEST_PER_POD,
            'total_memory_request': getattr(function, 'memory_request', cls.DEFAULT_MEMORY_REQUEST_PER_POD),
            'overall_efficiency': float(cls.DEFAULT_EFFICIENCY_PERCENT),
            'cold_start_count': cls.DEFAULT_COLD_START_COUNT
        }

    @classmethod
    def get_service_label_selector(cls, service_name: str) -> str:
        """Получить label selector для сервиса"""
        return cls.SERVICE_LABEL_SELECTOR.format(service_name=service_name)

    @classmethod
    def get_default_container_spec(cls, image: str, env_vars: list = None,
                                   memory: str = None, cpu: str = None) -> dict:
        """Получить дефолтную спецификацию контейнера"""
        if memory is None:
            memory = cls.DEFAULT_CONTAINER_MEMORY_REQUEST
        if cpu is None:
            cpu = cls.DEFAULT_CONTAINER_CPU_REQUEST

        return {
            "image": image,
            "env": env_vars or [],
            "resources": {
                "requests": {
                    "memory": memory,
                    "cpu": cpu
                }
            }
        }

    @classmethod
    def get_default_annotations(cls, min_scale: int = None, max_scale: int = None) -> dict:
        """Получить дефолтные аннотации для autoscaling"""
        if min_scale is None:
            min_scale = cls.DEFAULT_MIN_SCALE
        if max_scale is None:
            max_scale = cls.DEFAULT_MAX_SCALE

        return {
            cls.AUTOSCALING_MIN_ANNOTATION: str(min_scale),
            cls.AUTOSCALING_MAX_ANNOTATION: str(max_scale),
        }

    @classmethod
    def get_plan_limits(cls, tier: str) -> dict:
        """Получить лимиты для указанного тарифного плана"""
        tier_limits = {
            'STARTER': {
                'max_functions': cls.PLAN_LIMITS_STARTER_MAX_FUNCTIONS,
                'max_cpu_per_function': cls.PLAN_LIMITS_STARTER_MAX_CPU,
                'max_memory_per_function': cls.PLAN_LIMITS_STARTER_MAX_MEMORY,
                'max_scale': cls.PLAN_LIMITS_STARTER_MAX_SCALE,
            },
            'PROFESSIONAL': {
                'max_functions': cls.PLAN_LIMITS_PROFESSIONAL_MAX_FUNCTIONS,
                'max_cpu_per_function': cls.PLAN_LIMITS_PROFESSIONAL_MAX_CPU,
                'max_memory_per_function': cls.PLAN_LIMITS_PROFESSIONAL_MAX_MEMORY,
                'max_scale': cls.PLAN_LIMITS_PROFESSIONAL_MAX_SCALE,
            },
            'ENTERPRISE': {
                'max_functions': cls.PLAN_LIMITS_ENTERPRISE_MAX_FUNCTIONS,
                'max_cpu_per_function': cls.PLAN_LIMITS_ENTERPRISE_MAX_CPU,
                'max_memory_per_function': cls.PLAN_LIMITS_ENTERPRISE_MAX_MEMORY,
                'max_scale': cls.PLAN_LIMITS_ENTERPRISE_MAX_SCALE,
            }
        }

        return tier_limits.get(tier.upper(), tier_limits['STARTER'])


config = Config()
