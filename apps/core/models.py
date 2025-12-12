# apps/core/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from decimal import Decimal
import uuid
import logging
from django.contrib.auth import get_user_model
from apps.core.exceptions import DataIntegrityException # فرض بر این است که این استثنا وجود دارد
from apps.core.helpers import validate_ip_list # فرض بر این است که این تابع وجود دارد

logger = logging.getLogger(__name__)
User = get_user_model()

# --- مدل‌های پایه (Base Models) ---

class BaseModel(models.Model):
    """
    Base model with common fields like id, created_at, updated_at.
    This model is abstract and should be inherited by other models.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        abstract = True
        ordering = ['-created_at'] # Order by newest first by default

class TimeStampedModel(models.Model):
    """
    Another common base model for timestamping, if UUID is not needed as PK.
    Can be mixed with other abstract models.
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Created At"))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_("Updated At"))

    class Meta:
        abstract = True


class BaseOwnedModel(BaseModel):
    """
    Base model with an owner field.
    Useful for resources that belong to a specific user.
    """
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="%(class)s_owned", # e.g., 'strategy_owned', 'account_owned'
        verbose_name=_("Owner")
    )

    class Meta:
        abstract = True
        # Ensure no direct access without filtering by owner in most cases
        # Note: This doesn't prevent direct queries, but serves as a reminder.
        # Actual filtering should happen in Views/Services/Queries.

    def save(self, *args, **kwargs):
        """
        Override save to potentially log ownership changes or enforce constraints.
        """
        # مثال: چک کردن محدودیت‌های کاربر (مثلاً حداکثر تعداد ایجاد شده)
        # if not self.pk and self.__class__.objects.filter(owner=self.owner).count() >= MAX_ALLOWED:
        #     raise ValidationError("You have reached the maximum number of allowed instances.")
        super().save(*args, **kwargs)

    def clean(self):
        """
        Perform model-specific validation here.
        """
        super().clean()
        # مثال: اطمینان از اینکه owner یک کاربر تأیید شده است (اگر نیاز باشد)
        # if self.owner and not self.owner.is_verified:
        #     raise ValidationError({'owner': _('The owner must be a verified user.')})

# --- مدل‌های کاربردی Core ---

class AuditLog(BaseModel):
    """
    General audit log for tracking user actions on system resources.
    Essential for compliance, debugging, and security monitoring in an MAS.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # If user is deleted, keep the log entry
        null=True,
        blank=True,
        related_name="audit_logs",
        verbose_name=_("User")
    )
    action = models.CharField(max_length=64, verbose_name=_("Action")) # e.g., 'CREATE_ACCOUNT', 'PLACE_ORDER', 'UPDATE_STRATEGY'
    target_model = models.CharField(max_length=128, verbose_name=_("Target Model")) # e.g., 'Instrument', 'Strategy', 'Order'
    target_id = models.UUIDField(null=True, blank=True, verbose_name=_("Target ID")) # ID of the object acted upon
    details = models.JSONField(default=dict, blank=True, verbose_name=_("Details (JSON)")) # Extra context like old/new values, params
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name=_("IP Address"))
    user_agent = models.TextField(blank=True, verbose_name=_("User Agent"))
    session_key = models.CharField(max_length=40, blank=True, verbose_name=_("Session Key")) # If using sessions

    class Meta:
        verbose_name = _("Audit Log Entry")
        verbose_name_plural = _("Audit Log Entries")
        ordering = ['-created_at']

    def __str__(self):
        user_email = self.user.email if self.user else "Anonymous"
        return f"Audit: {user_email} - {self.action} on {self.target_model} ({self.target_id})"

    @classmethod
    def log_event(cls, user, action, target_model_name, target_id, details=None, request=None):
        """
        Class method to easily create an audit log entry.
        """
        details = details or {}
        ip_addr = None
        user_agent = None
        session_key = None

        if request:
            from apps.core.helpers import get_client_ip # import داخل تابع برای جلوگیری از حلقه
            ip_addr = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            session_key = getattr(request, 'session', {}).get('session_key', '')

        cls.objects.create(
            user=user,
            action=action,
            target_model=target_model_name,
            target_id=target_id,
            details=details,
            ip_address=ip_addr,
            user_agent=user_agent,
            session_key=session_key,
        )
        logger.info(f"Audit event logged: {action} on {target_model_name} ID {target_id} by {getattr(user, 'email', 'Anonymous')}.")


class SystemSetting(BaseModel):
    """
    Model for storing system-wide configuration settings.
    Allows runtime modification of system behavior.
    """
    DATA_TYPE_CHOICES = [
        ('str', _('String')),
        ('int', _('Integer')),
        ('float', _('Float')),
        ('bool', _('Boolean')),
        ('json', _('JSON')),
    ]
    key = models.CharField(max_length=128, unique=True, verbose_name=_("Setting Key"))
    value = models.TextField(verbose_name=_("Setting Value")) # Store as string, parse in code
    description = models.TextField(blank=True, verbose_name=_("Description"))
    data_type = models.CharField(
        max_length=16,
        choices=DATA_TYPE_CHOICES,
        default='str',
        verbose_name=_("Data Type")
    )
    is_sensitive = models.BooleanField(default=False, verbose_name=_("Is Sensitive (e.g., API key)"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))

    class Meta:
        verbose_name = _("System Setting")
        verbose_name_plural = _("System Settings")

    def __str__(self):
        masked_value = "***" if self.is_sensitive else self.value
        return f"{self.key} = {masked_value}"

    def get_parsed_value(self):
        """
        Parses the string value based on its declared data_type.
        """
        val = self.value
        if self.data_type == 'int':
            try:
                return int(val)
            except ValueError:
                logger.error(f"Failed to parse SystemSetting {self.key} as int: {val}")
                return None
        elif self.data_type == 'float':
            try:
                return float(val)
            except ValueError:
                logger.error(f"Failed to parse SystemSetting {self.key} as float: {val}")
                return None
        elif self.data_type == 'bool':
            return val.lower() in ['true', '1', 'yes', 'on']
        elif self.data_type == 'json':
            import json
            try:
                return json.loads(val)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse SystemSetting {self.key} as JSON: {val}")
                return {}
        return val # For 'str' type or if parsing fails

    def clean(self):
        """
        Validates the value based on its declared data_type.
        """
        super().clean()
        if self.data_type == 'int':
            try:
                int(self.value)
            except ValueError:
                raise ValidationError({'value': _('Value must be a valid integer for data type "int".')})
        elif self.data_type == 'float':
            try:
                float(self.value)
            except ValueError:
                raise ValidationError({'value': _('Value must be a valid float for data type "float".')})
        elif self.data_type == 'bool':
            if self.value.lower() not in ['true', 'false', '1', '0']:
                raise ValidationError({'value': _('Value must be "true", "false", "1", or "0" for data type "bool".')})
        elif self.data_type == 'json':
            import json
            try:
                json.loads(self.value)
            except json.JSONDecodeError:
                raise ValidationError({'value': _('Value must be a valid JSON string for data type "json".')})


class CacheEntry(BaseModel):
    """
    Model for application-level caching if Redis is not used or for specific needs.
    Stores key-value pairs with an optional TTL (Time To Live).
    """
    key = models.CharField(max_length=255, unique=True, verbose_name=_("Cache Key"))
    value = models.TextField(verbose_name=_("Cached Value")) # Store serialized data (JSON, Pickle string, etc.)
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Expires At"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Cache Entry")
        verbose_name_plural = _("Cache Entries")
        indexes = [
            models.Index(fields=['key']),
            models.Index(fields=['expires_at']), # For efficient cleanup
        ]

    def __str__(self):
        return f"Cache: {self.key}"

    def is_expired(self):
        """Checks if the cache entry has expired."""
        return self.expires_at and timezone.now() > self.expires_at

    @classmethod
    def get_cached_value(cls, key):
        """
        Class method to retrieve a value from the cache.
        Returns the value if found and not expired, otherwise None.
        """
        try:
            entry = cls.objects.get(key=key)
            if entry.is_expired():
                entry.delete() # Clean up expired entry
                logger.info(f"Expired cache entry '{key}' deleted.")
                return None
            logger.debug(f"Value for key '{key}' retrieved from database cache.")
            return entry.value
        except cls.DoesNotExist:
            logger.debug(f"Value for key '{key}' not found in database cache.")
            return None

    @classmethod
    def set_cached_value(cls, key, value, ttl_seconds=3600):
        """
        Class method to set a value in the cache.
        ttl_seconds: Time to live in seconds. If None, never expires.
        """
        try:
            expires_at = timezone.now() + timezone.timedelta(seconds=ttl_seconds) if ttl_seconds else None
            entry, created = cls.objects.update_or_create(
                key=key,
                defaults={
                    'value': value,
                    'expires_at': expires_at
                }
            )
            action = 'created' if created else 'updated'
            logger.debug(f"Cache entry for key '{key}' {action} in database cache.")
            return entry
        except Exception as e:
            logger.error(f"Error setting value in database cache for key '{key}': {str(e)}")
            raise DataIntegrityException(f"Failed to set cache entry: {str(e)}")

    @classmethod
    def invalidate_cache_key(cls, key):
        """
        Class method to invalidate (delete) a specific cache key.
        """
        deleted_count, _ = cls.objects.filter(key=key).delete()
        if deleted_count > 0:
            logger.info(f"Cache entry for key '{key}' invalidated from database cache.")
        else:
            logger.debug(f"No cache entry found for key '{key}' to invalidate.")


# --- مدل‌های مربوط به MAS ---
# این مدل‌ها ممکن است در اپلیکیشن جداگانه `agents` منطقی‌تر باشند، اما اگر در `core` قرار گیرند:
# class Agent(BaseModel):
#     """
#     Represents a generic agent in the MAS.
#     """
#     name = models.CharField(max_length=128, verbose_name=_("Agent Name"))
#     agent_type = models.CharField(max_length=64, verbose_name=_("Agent Type")) # e.g., data_collector, trader, risk_manager
#     owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="owned_agents")
#     is_active = models.BooleanField(default=True)
#     config = models.JSONField(default=dict, blank=True)
#     last_heartbeat = models.DateTimeField(null=True, blank=True)
#     status = models.CharField(max_length=32, default="IDLE")
#     class Meta:
#         verbose_name = _("Agent")
#         verbose_name_plural = _("Agents")
#     def __str__(self):
#         return f"{self.name} ({self.agent_type}) - Owner: {self.owner.username}"
#     def heartbeat(self):
#         self.last_heartbeat = timezone.now()
#         self.save(update_fields=['last_heartbeat'])

# class AgentLog(BaseModel):
#     agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name="logs")
#     level = models.CharField(max_length=16, choices=[('INFO', 'Info'), ('WARNING', 'Warning'), ('ERROR', 'Error')])
#     message = models.TextField()
#     extra_data = models.JSONField(default=dict, blank=True)
#     class Meta:
#         verbose_name = _("Agent Log")
#         verbose_name_plural = _("Agent Logs")
#         ordering = ['-created_at']
#     def __str__(self):
#         return f"[{self.level}] {self.agent.name}: {self.message[:50]}..."

# --- مدل‌های مربوط به لاگ و مانیتورینگ ---
# class SystemLog(BaseModel):
#     level = models.CharField(max_length=16)
#     message = models.TextField()
#     component = models.CharField(max_length=128) # e.g., 'core', 'market_data', 'trading_engine'
#     trace_id = models.CharField(max_length=128, blank=True) # برای ردیابی در MAS
#     class Meta:
#         verbose_name = _("System Log")
#         verbose_name_plural = _("System Logs")
#         ordering = ['-created_at']
#     def __str__(self):
#         return f"[{self.level}] {self.component}: {self.message[:50]}..."

# --- مدل‌های مربوط به مدیریت کاربر ---
# مدل CustomUser در اپلیکیشن `accounts` قرار دارد و نباید اینجا تکرار شود.
# اما اگر نیاز به مدل‌های مرتبط با کاربر در `core` باشد (مثل یک سابقه فعالیت کلی)، می‌توان آن را اینجا قرار داد.
# class UserActivityLog(BaseModel):
#     user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="activity_logs")
#     action = models.CharField(max_length=64) # e.g., 'logged_in', 'api_call_made'
#     details = models.JSONField(default=dict, blank=True)
#     ip_address = models.GenericIPAddressField(null=True, blank=True)
#     class Meta:
#         verbose_name = _("User Activity Log")
#         verbose_name_plural = _("User Activity Logs")
#         ordering = ['-created_at']
#     def __str__(self):
#         return f"{self.user.username} - {self.action}"

# --- مدل‌های مربوط به تنظیمات کاربر ---
# class UserSetting(BaseOwnedModel): # از BaseOwnedModel استفاده می‌کند
#     setting_key = models.CharField(max_length=128)
#     setting_value = models.TextField()
#     is_active = models.BooleanField(default=True)
#     class Meta:
#         unique_together = ('owner', 'setting_key') # هر کاربر فقط یک مقدار برای هر کلید داشته باشد
#         verbose_name = _("User Setting")
#         verbose_name_plural = _("User Settings")
#     def __str__(self):
#         return f"{self.owner.username} - {self.setting_key}"

logger.info("Core models loaded successfully.")
