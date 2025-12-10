# apps/accounts/managers.py

from django.contrib.auth.models import BaseUserManager
from django.db import models
from django.utils import timezone
from typing import Optional

class UserAPIKeyManager(models.Manager):
    """
    Custom manager for UserAPIKey model with additional query methods.
    """
    def active(self):
        """
        Returns active API keys.
        """
        return self.filter(is_active=True)

    def expired(self):
        """
        Returns expired API keys (those with an expiry date in the past).
        """
        return self.filter(expires_at__lt=timezone.now(), is_active=True)

    def for_user(self, user):
        """
        Returns API keys belonging to a specific user.
        """
        return self.filter(user=user)

    def valid_for_user(self, user):
        """
        Returns API keys that are both active and not expired for a specific user.
        """
        now = timezone.now()
        return self.filter(
            user=user,
            is_active=True,
            expires_at__isnull=True  # No expiry date
        ).union(
            self.filter(user=user, is_active=True, expires_at__gte=now) # Expiry date in future
        )

    def get_by_key_string(self, key_string: str) -> Optional['UserAPIKey']: # تغییر نام از get_by_key به get_by_key_string
        """
        Retrieves an API key object by its string value.
        """
        try:
            return self.get(key=key_string, is_active=True)
        except self.model.DoesNotExist:
            return None

# نکته: این منیجر باید در مدل UserAPIKey به صورت زیر استفاده شود:
# class UserAPIKey(BaseModel):
#     # ... فیلدها ...
#     objects = UserAPIKeyManager() # استفاده از منیجر سفارشی
