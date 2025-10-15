from typing import Optional, Any

from django.contrib.auth.backends import ModelBackend
from django.core.exceptions import ObjectDoesNotExist  # ← ДОБАВИТЬ ЭТОТ ИМПОРТ
from django.http import HttpRequest

from .models import User


class EmailBackend(ModelBackend):
    """Authenticate using email instead of username"""

    def authenticate(
        self,
        request: Optional[HttpRequest],
        email: Optional[str]=None, password:
        Optional[str]=None, **kwargs: Any
    ) -> Optional[User]:
        try:
            user = User.objects.get(email=email)
            if user.check_password(password):
                return user
        except ObjectDoesNotExist:
            return None
