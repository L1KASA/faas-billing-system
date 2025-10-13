# Faas Billing System

## Установка и запуск
### 1. Создать виртуальное окружение
#### Windows:
````
1. python -m venv venv
2. venv\Scripts\activate
````
#### Linux/macOS:
````
python -m venv venv
source venv/bin/activate
````
#### 2. Установить зависимости
````
pip install -r requirements.txt
````
#### 3. Создать файл .env
Скопировать и заполнить по образцу .env.example

**P.S.** Секретный ключ Django для dev среды генерируется автоматически

#### 4. Применить миграции
````
python manage.py migrate
````
#### 5. Создать суперпользователя (опционально)
```
python manage.py createsuperuser
```
#### 4. Запустить сервер 
```
python manage.py runserver
```
#### 6. Открыть в браузере
* Главная страница: http://127.0.0.1:8000/
* Админка: http://127.0.0.1:8000/admin/

## Структура проекта

## Основные возможности