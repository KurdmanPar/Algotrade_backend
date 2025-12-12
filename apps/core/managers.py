# apps/core/managers.py

from django.db import models
from django.utils import timezone
from decimal import Decimal
import logging
from .models import (
    BaseModel,
    BaseOwnedModel,
    TimeStampedModel,
    AuditLog,
    SystemSetting,
    CacheEntry,
    # سایر مدل‌هایی که در core تعریف کرده‌اید
    # InstrumentGroup,
    # InstrumentCategory,
    # Instrument,
    # InstrumentExchangeMap,
    # IndicatorGroup,
    # Indicator,
    # IndicatorParameter,
    # IndicatorTemplate,
    # PriceActionPattern,
    # SmartMoneyConcept,
    # AIMetric,
    # InstrumentWatchlist,
)

logger = logging.getLogger(__name__)

# --- QuerySets سفارشی ---

class CoreBaseQuerySet(models.QuerySet):
    """
    Custom QuerySet for the base model with common filtering methods.
    """
    def active(self):
        """
        Filters for objects that are considered 'active'.
        Assumes the model has an 'is_active' boolean field.
        """
        return self.filter(is_active=True)

    def inactive(self):
        """
        Filters for objects that are not active.
        """
        return self.exclude(is_active=True)

    def created_after(self, date):
        """
        Filters objects created after a specific date/time.
        """
        return self.filter(created_at__gt=date)

    def created_before(self, date):
        """
        Filters objects created before a specific date/time.
        """
        return self.filter(created_at__lt=date)

    def updated_after(self, date):
        """
        Filters objects updated after a specific date/time.
        """
        return self.filter(updated_at__gt=date)

    def updated_before(self, date):
        """
        Filters objects updated before a specific date/time.
        """
        return self.filter(updated_at__lt=date)

    # می‌توانید متد‌های دیگری مانند search، order_by_priority و غیره اضافه کنید
    # مثلاً:
    # def search(self, query):
    #     return self.filter(Q(name__icontains=query) | Q(description__icontains=query))


class CoreOwnedModelQuerySet(CoreBaseQuerySet):
    """
    Custom QuerySet for models that have an 'owner' field.
    Extends CoreBaseQuerySet to add owner-specific methods.
    """
    def owned_by(self, user):
        """
        Filters objects owned by a specific user.
        Assumes the model has an 'owner' ForeignKey field.
        """
        return self.filter(owner=user)

    def not_owned_by(self, user):
        """
        Filters objects *not* owned by a specific user.
        """
        return self.exclude(owner=user)

    def for_user(self, user):
        """
        Alias for owned_by.
        """
        return self.owned_by(user)

    # مثال: فیلتر بر اساس مالک و وضعیت فعال
    def owned_active(self, user):
        """
        Filters active objects owned by a specific user.
        """
        return self.owned_by(user).active()


class TimeStampedModelQuerySet(models.QuerySet):
    """
    Custom QuerySet for models with 'created_at' and 'updated_at' fields.
    """
    def recently_created(self, hours=24):
        """
        Filters objects created within the last N hours.
        """
        cutoff_time = timezone.now() - timezone.timedelta(hours=hours)
        return self.filter(created_at__gte=cutoff_time)

    def recently_updated(self, hours=24):
        """
        Filters objects updated within the last N hours.
        """
        cutoff_time = timezone.now() - timezone.timedelta(hours=hours)
        return self.filter(updated_at__gte=cutoff_time)

    def older_than(self, days=30):
        """
        Filters objects older than N days.
        """
        cutoff_time = timezone.now() - timezone.timedelta(days=days)
        return self.filter(created_at__lt=cutoff_time)

    def created_between_dates(self, start_date, end_date):
        """
        Filters objects created between two dates.
        """
        return self.filter(created_at__date__gte=start_date.date(), created_at__date__lte=end_date.date())


# --- منیجرهای سفارشی ---

class CoreBaseManager(models.Manager):
    """
    Custom Manager for the base model.
    Uses the custom CoreBaseQuerySet.
    """
    def get_queryset(self):
        return CoreBaseQuerySet(self.model, using=self._db)


class CoreOwnedModelManager(CoreBaseManager):
    """
    Custom Manager for models that have an 'owner' field.
    Uses the custom CoreOwnedModelQuerySet.
    """
    def get_queryset(self):
        return CoreOwnedModelQuerySet(self.model, using=self._db)

    # می‌توانید متد‌هایی که فقط یک شیء برمی‌گردانند یا منطق خاصی دارند را اینجا تعریف کنید
    # مثلاً:
    # def get_by_owner_and_id(self, user, obj_id):
    #     try:
    #         return self.get_queryset().owned_by(user).get(id=obj_id)
    #     except self.model.DoesNotExist:
    #         return None


class TimeStampedModelManager(models.Manager):
    """
    Custom Manager for models with 'created_at' and 'updated_at' fields.
    Uses the custom TimeStampedModelQuerySet.
    """
    def get_queryset(self):
        return TimeStampedModelQuerySet(self.model, using=self._db)


# --- منیجرهای مدل‌های خاص Core ---

class AuditLogQuerySet(CoreBaseQuerySet):
    """
    Custom QuerySet for AuditLog model with specific methods.
    """
    def for_user(self, user):
        """Filters audit logs for a specific user."""
        return self.filter(user=user)

    def for_target(self, target_model_name: str, target_id):
        """Filters audit logs for a specific target object."""
        return self.filter(target_model=target_model_name, target_id=target_id)

    def for_action(self, action: str):
        """Filters audit logs for a specific action."""
        return self.filter(action__iexact=action)

    def in_date_range(self, start_date, end_date):
        """Filters audit logs within a specific date range."""
        return self.filter(created_at__date__gte=start_date.date(), created_at__date__lte=end_date.date())

    def failed_actions(self):
        """Filters audit logs for actions that resulted in failure/error."""
        # فرض: فیلد details یک JSON است و ممکن است پیام خطا را شامل شود
        # ممکن است نیاز به جستجوی JSON باشد
        return self.filter(details__contains={'status': 'failed'}) # یا استفاده از Q objects برای جستجوهای پیچیده‌تر

    def successful_actions(self):
        """Filters audit logs for actions that were successful."""
        return self.filter(details__contains={'status': 'success'})


class AuditLogManager(CoreBaseManager):
    """
    Manager for AuditLog model.
    """
    def get_queryset(self):
        return AuditLogQuerySet(self.model, using=self._db)


class SystemSettingQuerySet(CoreBaseQuerySet):
    """
    Custom QuerySet for SystemSetting model.
    """
    def active(self):
        """Filters active settings."""
        return self.filter(is_active=True)

    def sensitive(self):
        """Filters sensitive settings."""
        return self.filter(is_sensitive=True)

    def by_key(self, key: str):
        """Filters by a specific key (case-insensitive)."""
        return self.filter(key__iexact=key)

    def get_value_by_key(self, key: str, default=None):
        """
        Convenience method to get the parsed value of a setting by its key.
        """
        try:
            setting = self.by_key(key).active().first()
            if setting:
                return setting.get_parsed_value()
            else:
                return default
        except Exception as e:
            logger.error(f"Error fetching system setting value for key '{key}': {str(e)}")
            return default


class SystemSettingManager(CoreBaseManager):
    """
    Manager for SystemSetting model.
    """
    def get_queryset(self):
        return SystemSettingQuerySet(self.model, using=self._db)

    def get_cached_value(self, key: str, default=None, cache_timeout: int = 3600):
        """
        Retrieves a system setting value, preferably from cache.
        Falls back to database if not cached or expired.
        """
        from django.core.cache import cache
        cache_key = f"sys_setting_{key.lower()}"
        cached_val = cache.get(cache_key)
        if cached_val is not None:
            logger.debug(f"System setting '{key}' retrieved from cache.")
            return cached_val

        # اگر در کش نبود، از دیتابیس بخوان
        val = self.get_queryset().get_value_by_key(key, default)
        if val is not None: # فقط اگر مقداری وجود داشت، در کش قرار بده
            cache.set(cache_key, val, timeout=cache_timeout)
            logger.debug(f"System setting '{key}' retrieved from DB and cached.")
        return val

    def set_value(self, key: str, value, data_type: str = 'str', description: str = "", is_sensitive: bool = False):
        """
        Creates or updates a system setting.
        Clears the cache entry after update.
        """
        from django.core.cache import cache
        cache_key = f"sys_setting_{key.lower()}"
        try:
            setting, created = self.update_or_create(
                key=key,
                defaults={
                    'value': str(value), # Always store as string
                    'data_type': data_type,
                    'description': description,
                    'is_sensitive': is_sensitive,
                    'is_active': True, # معمولاً وقتی می‌سازیم، فعال است
                }
            )
            # پاک کردن کش بعد از بروزرسانی
            cache.delete(cache_key)
            logger.info(f"System setting '{key}' {'created' if created else 'updated'} and cache cleared.")
            return setting
        except Exception as e:
            logger.error(f"Error setting system setting '{key}': {str(e)}")
            raise # یا مدیریت خطا مناسب


class CacheEntryQuerySet(CoreBaseQuerySet):
    """
    Custom QuerySet for CacheEntry model.
    """
    def expired(self):
        """
        Filters entries that have expired.
        """
        now = timezone.now()
        return self.filter(expires_at__lt=now, is_active=True)

    def active(self):
        """
        Filters entries that are not expired and are active.
        """
        now = timezone.now()
        return self.filter(expires_at__gte=now, is_active=True)

    def by_key(self, key: str):
        """
        Filters by a specific cache key.
        """
        return self.filter(key__iexact=key)


class CacheEntryManager(CoreBaseManager):
    """
    Manager for CacheEntry model.
    """
    def get_queryset(self):
        return CacheEntryQuerySet(self.model, using=self._db)

    def get_from_db_cache(self, key: str):
        """
        Retrieves a value from the database cache table if it exists and is not expired.
        """
        try:
            entry = self.active().by_key(key).first() # استفاده از QuerySet سفارشی
            if entry:
                logger.debug(f"Value for key '{key}' retrieved from database cache.")
                return entry.value
            logger.debug(f"Value for key '{key}' not found in database cache.")
            return None
        except Exception as e:
            logger.error(f"Error retrieving from database cache for key '{key}': {str(e)}")
            return None

    def set_in_db_cache(self, key: str, value: str, ttl_seconds: int = 3600):
        """
        Sets a value in the database cache table.
        """
        try:
            expires_at = timezone.now() + timezone.timedelta(seconds=ttl_seconds) if ttl_seconds else None
            entry, created = self.update_or_create(
                key=key,
                defaults={
                    'value': value,
                    'expires_at': expires_at,
                    'is_active': True
                }
            )
            action = 'created' if created else 'updated'
            logger.debug(f"Value for key '{key}' {action} in database cache.")
            return entry
        except Exception as e:
            logger.error(f"Error setting value in database cache for key '{key}': {str(e)}")
            raise # یا مدیریت خطا مناسب


# --- منیجرهای مدل‌های دیگر (اگر در core باشند) ---
# می‌توانید برای سایر مدل‌هایی که در apps/core/models.py تعریف کرده‌اید نیز QuerySet و Manager سفارشی بنویسید.
# مثلاً اگر مدل SmartMoneyConcept در core بود:
# class SmartMoneyConceptQuerySet(CoreBaseQuerySet):
#     def active(self):
#         return self.filter(is_active=True)
#
# class SmartMoneyConceptManager(CoreBaseManager):
#     def get_queryset(self):
#         return SmartMoneyConceptQuerySet(self.model, using=self._db)
#
# # و در ادمین:
# # admin.site.register(SmartMoneyConcept, admin.ModelAdmin, manager=SmartMoneyConceptManager())

# --- مثال: منیجر برای InstrumentWatchlist ---
# اگر InstrumentWatchlist در اپلیکیشن instruments بود، اما به دلیل وابستگی به core، اینجا نیز می‌توانید منیجر آن را ایجاد کنید.
# اما ترجیحاً در اپلیکیشن مربوطه (instruments) قرار می‌گیرد.
# اگر core شامل مدل‌های مشابهی باشد، می‌توانید به صورت زیر ایجاد کنید:
# class InstrumentWatchlistQuerySet(CoreOwnedModelQuerySet):
#     def public(self):
#         return self.filter(is_public=True)
#     def containing_instrument(self, instrument_id):
#         return self.filter(instruments__id=instrument_id)
#
# class InstrumentWatchlistManager(CoreOwnedModelManager):
#     def get_queryset(self):
#         return InstrumentWatchlistQuerySet(self.model, using=self._db)

logger.info("Core managers loaded successfully.")
