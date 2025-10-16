# Faas Billing System

## Developer staff
* [selivanova-a](https://github.com/selivanova-a) - Frontend Developer
* [h4cktivist](https://github.com/h4cktivist) - Backend Developer
* [L1KASA](https://github.com/L1KASA) - Backend Developer
* [Arigos](https://t.me/Arigos) - Graphic Designer

## Требования к окружению:
- ОЗУ: 8 GB (рекомендуется: 16 GB)
- CPU: 4 ядра
- Диск: 50 GB свободного места

## Установка и запуск Django
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
### 2. Установить зависимости
````
pip install -r requirements.txt
````
### 3. Создать файл .env
Скопировать и заполнить по образцу .env.example

**P.S.** Секретный ключ Django для dev среды генерируется автоматически

### 4. Применить миграции
````
python manage.py migrate
````
### 5. Создать суперпользователя (опционально)
```
python manage.py createsuperuser
```
### 6. Прописать команду для создания уже готового тарифного плана
```
python manage.py create_default_plans
```
### 7. Запустить сервер 
```
python manage.py runserver
```
### 8. Открыть в браузере
* Главная страница: http://127.0.0.1:8000/users/
* Админка: http://127.0.0.1:8000/admin/

## Полная инструкция для Windows
### Установить необходимые инструменты
#### Docker Desktop
#### Git Bash
#### Python 3.11+

### Установить Knative через Git Bash
```
# 1. Скачать скрипт установки Knative
curl -LO https://raw.githubusercontent.com/your-repo/install_knative_1_17_kourier.sh

# 2. Дать права на выполнение
chmod +x install_knative_1_17_kourier.sh

# 3. Запустить установку
./install_knative_1_17_kourier.sh
```
### Если скрипта нет, установить вручную
```
# Установка Knative вручную
kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.17.0/serving-crds.yaml
kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.17.0/serving-core.yaml
kubectl apply -f https://github.com/knative/net-kourier/releases/download/knative-v1.17.0/kourier.yaml

# Установка Metrics API
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl patch deployment metrics-server -n kube-system --type='json' -p='[{"op": "add", "path": "/spec/template/spec/containers/0/args/-", "value": "--kubelet-insecure-tls"}]'

# Настройка сети
kubectl patch configmap/config-network \
  --namespace knative-serving \
  --type merge \
  --patch '{"data":{"ingress-class":"kourier.ingress.networking.knative.dev"}}'

# Настройка домена
kubectl patch configmap/config-domain \
  --namespace knative-serving \
  --type merge \
  --patch '{"data":{"knative.demo.com":""}}'
```
### Настроить и поднять проект Django (перейти к пунктам выше, выполнить все до запуска сервера)
### Проверить, что Knative и тестовый сервис работают
```
kubectl get pods -n knative-serving

curl -H "Host: echo.default.knative.demo.com" "http://localhost:80"
```
### В браузере открыть: http://localhost:8000/functions/
### Деплой функции через Django
#### Нажать "Deploy New Function"
```
Name: echo-server
Docker Image: ealen/echo-server:latest
Min Scale: 0
Max Scale: 3

Name: hello-python
Docker Image: python:3.11-slim
Min Scale: 0
Max Scale: 2
```
### Проверить в Git Bash
```
kubectl get ksvc
kubectl get pods -l serving.knative.dev/service=test-function
```
### Тестирование функции
#### После деплоя протестировать
```
# В Git Bash с port-forward
kubectl port-forward -n kourier-system service/kourier 8080:80

# В другом окне Git Bash
curl -H "Host: test-function.default.knative.demo.com" "http://localhost:8080"

Или в PowerShell:
# Если port-forward работает на 8080
curl.exe -H "Host: test-function.default.knative.demo.com" http://localhost:8080
```
### 🚨 Решение проблем на Windows
```
# Попробовать использовать другой порт
kubectl port-forward -n kourier-system service/kourier 8081:80

# Если Django не видит Kubernetes:
# Проверьте контекст в Git Bash
kubectl config get-contexts
kubectl config use-context docker-desktop

# Проверьте что kubectl работает
kubectl get nodes
```
### ✅ Быстрая проверка работоспособности
В Git Bash:
```
# 1. Проверить Kubernetes
kubectl get nodes

# 2. Проверить Knative
kubectl get pods -n knative-serving

# 3. Тест функции
kubectl get ksvc

# 4. Запустите port-forward
kubectl port-forward -n kourier-system service/kourier 8080:80
```
В браузере: http://localhost:8000/functions/
В PowerShell:
```
# Тест функции
curl.exe -H "Host: test-function.default.knative.demo.com" http://localhost:8080
```
## Структура проекта
```
faas-billing-system/
├── manage.py
├── Dockerfile
├── test_function.py
├── requirements.txt
├── .env
├── .env.example
├── faas_billing/
│   ├── asgi.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── functions/
│   ├── models.py
│   ├── views.py
│   ├── knative_manager.py
│   └── urls.py
├── users/
│   ├── models.py
│   ├── backencds.py
│   ├── exceptions.py
│   ├── mixins.py
│   ├── permissions.py
│   ├── services.py
│   ├── views.py
│   └── urls.py
├── billing/
│   ├── management/commands/create_default_plans.py
│   ├── seed_tariff_plans.py
│   ├── subscription_manager.py
│   ├── views.py
│   └── urls.py
├── tarif_plan/
│   ├── models.py
│   ├── billing_calculator.py
│   ├── metrics_manager.py
│   ├── views.py
│   └── urls.py
├── templates/
└── k8s/
    ├── postgres.yaml
    ├── ingress.yaml
    ├── secrets.yaml
    └── django-deployment.yaml
```
## Основные возможности
- ✅ **Деплой FaaS функций** через веб-интерфейс
- ✅ **Автоматическое масштабирование** (от 0 до N подов)
- ✅ **Управление функциями** (создание, просмотр, удаление)
- ✅ **Вызов функций** по уникальным URL
- ✅ **Интеграция с Kubernetes** через Django

