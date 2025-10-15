import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'faas_billing.settings')
django.setup()

from functions.knative_manager import KnativeManager


def test_knative_connection():
    print("Testing Knative connection...")
    manager = KnativeManager()

    # Проверка списка функций
    result = manager.list_functions()
    print("List functions:", "SUCCESS" if result['success'] else "FAILED")

    if result['success']:
        print("Existing functions:", len(result['data']))
        for func in result['data']:
            print(f" - {func['metadata']['name']}")
    else:
        print("Error:", result['error'])


if __name__ == "__main__":
    test_knative_connection()