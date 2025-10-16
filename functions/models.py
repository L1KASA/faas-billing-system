from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Function(models.Model):
    class FunctionStatus(models.TextChoices):
        DEPLOYING = 'DEPLOYING', 'Deploying'
        READY = 'READY', 'Ready'
        FAILED = 'FAILED', 'Failed'
        DELETING = 'DELETING', 'Deleting'

    name = models.CharField(max_length=100, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='functions')
    docker_image = models.CharField(max_length=500)
    status = models.CharField(max_length=20, choices=FunctionStatus.choices, default=FunctionStatus.DEPLOYING)
    knative_service_name = models.CharField(max_length=100)
    url = models.URLField(blank=True)

    # Configuration
    min_scale = models.IntegerField(default=0)
    max_scale = models.IntegerField(default=5)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    metrics = models.JSONField(default=dict)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.knative_service_name:
            self.knative_service_name = self.name
        super().save(*args, **kwargs)
