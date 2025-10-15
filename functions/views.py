from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import ListView, DetailView

from .models import Function
from .knative_manager import KnativeManager


@login_required
def function_list(request):
    """Список всех функций пользователя"""
    functions = Function.objects.filter(user=request.user)

    # Обновляем статусы функций из Knative
    knative_manager = KnativeManager()
    for function in functions:
        if function.status in [Function.FunctionStatus.READY, Function.FunctionStatus.DEPLOYING]:
            status_result = knative_manager.get_function_status(function.name)
            if status_result['success']:
                knative_data = status_result['data']
                # Можно обновить статус на основе данных из Knative
                # function.status = Function.FunctionStatus.READY
                # function.save()

    return render(request, 'functions/function_list.html', {
        'functions': functions
    })


@login_required
def deploy_function(request):
    """Деплой новой функции"""
    if request.method == 'POST':
        name = request.POST.get('name')
        docker_image = request.POST.get('docker_image')
        min_scale = int(request.POST.get('min_scale', 0))
        max_scale = int(request.POST.get('max_scale', 5))

        # Проверяем, существует ли уже функция с таким именем
        if Function.objects.filter(name=name).exists():
            messages.error(request, f'Function with name "{name}" already exists.')
            return render(request, 'functions/deploy_function.html')

        # Создаем запись в базе
        function = Function.objects.create(
            name=name,
            user=request.user,
            docker_image=docker_image,
            min_scale=min_scale,
            max_scale=max_scale,
            status=Function.FunctionStatus.DEPLOYING
        )

        # Деплоим в Knative
        knative_manager = KnativeManager()

        # Environment variables
        env_vars = {
            'FUNCTION_NAME': name,
            'USER_ID': str(request.user.id),
            'DEPLOYED_VIA': 'django-faas-platform'
        }

        result = knative_manager.deploy_function(
            name=name,
            image=docker_image,
            env_vars=env_vars,
            min_scale=min_scale,
            max_scale=max_scale
        )

        if result['success']:
            function.status = Function.FunctionStatus.READY
            function.url = f"http://{name}.default.knative.demo.com"  # Ваш домен из Knative
            function.save()
            messages.success(request, f'Function "{name}" deployed successfully!')
        else:
            function.status = Function.FunctionStatus.FAILED
            function.save()
            messages.error(request, f'Failed to deploy function: {result["error"]}')

        return redirect('functions:function_list')

    return render(request, 'functions/deploy_function.html')


@login_required
def function_detail(request, pk):
    """Детальная информация о функции"""
    function = get_object_or_404(Function, pk=pk, user=request.user)

    # Получаем актуальный статус из Knative
    knative_manager = KnativeManager()
    status_result = knative_manager.get_function_status(function.name)

    knative_data = {}
    if status_result['success']:
        knative_data = status_result['data']

    return render(request, 'functions/function_detail.html', {
        'function': function,
        'knative_data': knative_data
    })


@login_required
def delete_function(request, pk):
    """Удаление функции"""
    function = get_object_or_404(Function, pk=pk, user=request.user)

    if request.method == 'POST':
        function.status = Function.FunctionStatus.DELETING
        function.save()

        knative_manager = KnativeManager()
        result = knative_manager.delete_function(function.name)

        if result['success']:
            function.delete()
            messages.success(request, f'Function "{function.name}" deleted successfully!')
        else:
            messages.error(request, f'Failed to delete function: {result["error"]}')
            function.status = Function.FunctionStatus.READY
            function.save()

        return redirect('functions:function_list')

    return render(request, 'functions/function_confirm_delete.html', {
        'function': function
    })


@login_required
def invoke_function(request, pk):
    """Вызов функции (редирект на URL функции)"""
    function = get_object_or_404(Function, pk=pk, user=request.user)

    if function.status != Function.FunctionStatus.READY:
        messages.error(request, f'Function "{function.name}" is not ready for invocation.')
        return redirect('functions:function_detail', pk=pk)

    # Здесь может быть логика прямого вызова через API
    # Пока просто показываем URL
    messages.info(request, f'Function URL: {function.url}')
    return redirect('functions:function_detail', pk=pk)


@login_required
def function_status_api(request, pk):
    """API для получения статуса функции"""
    function = get_object_or_404(Function, pk=pk, user=request.user)

    knative_manager = KnativeManager()
    status_result = knative_manager.get_function_status(function.name)

    return JsonResponse({
        'function_id': function.id,
        'function_name': function.name,
        'django_status': function.status,
        'knative_status': status_result
    })
