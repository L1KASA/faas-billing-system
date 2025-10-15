FROM python:3.11-slim

WORKDIR /app

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копирование зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование кода
COPY . .

# Создание директории для статики
RUN mkdir -p staticfiles

# Сборка статики (пропустим если нет статики)
RUN python manage.py collectstatic --noinput || echo "No static files to collect"

# Запуск сервера
CMD ["gunicorn", "faas_billing.wsgi:application", "--bind", "0.0.0.0:8000"]