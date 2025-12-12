# apps/core/services.py

from typing import Dict, List, Optional, Any
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.cache import cache
from django.conf import settings
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
from .exceptions import (
    CoreSystemException,
    DataIntegrityException,
    ConfigurationError,
    # سایر استثناهای سفارشی شما
    AuditLogError,
    CacheError,
    CacheMissError,
    CacheSyncError,
)
from .helpers import (
    # توابع کمکی احتمالی
    # validate_ip_list,
    # is_ip_in_allowed_list,
    # normalize_data_from_source,
    # validate_ohlcv_data,
    # get_client_ip,
    # generate_device_fingerprint,
    # mask_sensitive_data,
    # hash_data,
)
from apps.accounts.models import CustomUser # فرض بر این است که مدل وجود دارد

logger = logging.getLogger(__name__)

class CoreService:
    """
    Service class for handling core system business logic.
    This includes common operations like audit logging, system settings management,
    data validation, and interaction with external services or other apps.
    """
    # --- منطق مربوط به لاگ حسابرسی (Audit Log) ---
    @staticmethod
    def log_action(user, action: str, target_model: str, target_id, details: Dict[str, Any] = None, request=None):
        """
        Logs an action/event to the AuditLog model.
        Optionally extracts IP and User-Agent from the request object.
        """
        details = details or {}
        ip_addr = None
        user_agent = None
        session_key = None

        if request:
            from .helpers import get_client_ip # import داخل تابع برای جلوگیری از حلقه
            ip_addr = get_client_ip(request)
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            session_key = getattr(request, 'session', {}).get('session_key', '')

        audit_entry = AuditLog.objects.create(
            user=user,
            action=action,
            target_model=target_model,
            target_id=target_id,
            details=details,
            ip_address=ip_addr,
            user_agent=user_agent,
            session_key=session_key,
        )
        logger.info(f"Audit event '{action}' logged for {target_model} ID {target_id} by user {getattr(user, 'email', 'Anonymous')}.")
        return audit_entry

    # --- منطق مربوط به تنظیمات سیستم (System Settings) ---
    @staticmethod
    def get_system_setting_value(key: str, default=None, use_cache: bool = True):
        """
        Retrieves a system setting value, preferably from cache.
        Falls back to database if not cached or expired.
        """
        cache_key = f"sys_setting_{key.lower()}"
        if use_cache:
            cached_val = cache.get(cache_key)
            if cached_val is not None:
                logger.debug(f"System setting '{key}' retrieved from cache.")
                return cached_val

        # اگر در کش نبود یا استفاده از کش غیرفعال بود
        try:
            setting = SystemSetting.objects.get(key__iexact=key, is_active=True)
            parsed_val = setting.get_parsed_value()
            if use_cache:
                # کش کردن مقدار برای 1 ساعت (یا از مقدار دیگری از تنظیمات)
                cache_timeout = getattr(settings, 'SYS_SETTING_CACHE_TIMEOUT', 3600)
                cache.set(cache_key, parsed_val, timeout=cache_timeout)
                logger.debug(f"System setting '{key}' retrieved from DB and cached.")
            return parsed_val
        except SystemSetting.DoesNotExist:
            logger.warning(f"System setting with key '{key}' not found.")
            cache.set(cache_key, default, timeout=60) # مقدار پیش‌فرض را برای مدت کوتاهی کش کن تا از درخواست‌های متعدد جلوگیری شود
            return default
        except Exception as e:
            logger.error(f"Error fetching system setting '{key}': {str(e)}")
            return default

    @staticmethod
    def update_system_setting(key: str, new_value, data_type: str = None, description: str = "", is_sensitive: bool = None):
        """
        Creates or updates a system setting.
        Clears the cache entry after update.
        """
        try:
            # اگر data_type یا is_sensitive ارائه شده باشد، باید مدل وجود داشته باشد یا باید قبل از فراخوانی این تابع اعتبارسنجی شود
            update_fields = ['value']
            defaults = {'value': str(new_value)}
            if data_type:
                defaults['data_type'] = data_type
                update_fields.append('data_type')
            if description:
                defaults['description'] = description
                update_fields.append('description')
            if is_sensitive is not None: # is_sensitive می‌تواند False باشد، بنابراین فقط اگر None نبود بروزرسانی کن
                defaults['is_sensitive'] = is_sensitive
                update_fields.append('is_sensitive')

            setting, created = SystemSetting.objects.update_or_create(
                key=key,
                defaults=defaults
            )
            if not created:
                # اگر موجود بود، فقط فیلدهای مشخص شده را بروزرسانی کن
                for field in update_fields:
                    setattr(setting, field, defaults[field])
                setting.save(update_fields=update_fields)

            # پاک کردن کش
            cache_key = f"sys_setting_{key.lower()}"
            cache.delete(cache_key)
            logger.info(f"System setting '{key}' {'created' if created else 'updated'} and cache cleared.")
            return setting
        except Exception as e:
            logger.error(f"Error updating system setting '{key}': {str(e)}")
            raise ConfigurationError(f"Failed to update system setting '{key}': {str(e)}")

    # --- منطق مربوط به کش (Cache) ---
    @staticmethod
    def get_cached_value(key: str, use_db_fallback: bool = True, mask_if_sensitive: bool = False) -> Optional[Any]:
        """
        Retrieves a value from the external cache (e.g., Redis).
        Optionally falls back to the database cache model if not found externally.
        Optionally masks the value if it seems sensitive based on the key.
        """
        # اول از کش خارجی (Redis/Memcached)
        cached_val = cache.get(key)
        if cached_val is not None:
            logger.debug(f"Value for key '{key}' retrieved from external cache.")
            if mask_if_sensitive and any(keyword in key.lower() for keyword in ['api', 'key', 'secret', 'token']):
                 return mask_sensitive_data(cached_val) if callable(mask_sensitive_data) else cached_val
            return cached_val

        # اگر در کش خارجی نبود و فبل‌بک مجاز است
        if use_db_fallback:
            try:
                from .models import CacheEntry # import داخل تابع
                entry = CacheEntry.objects.get(key=key)
                if entry.is_expired():
                    logger.info(f"DB cache entry '{key}' is expired. Deleting.")
                    entry.delete()
                    return None
                logger.debug(f"Value for key '{key}' retrieved from database cache.")
                # اینجا نیز می‌توانید منطق مسک کردن را اعمال کنید
                if mask_if_sensitive and any(keyword in key.lower() for keyword in ['api', 'key', 'secret', 'token']):
                     return mask_sensitive_data(entry.value) if callable(mask_sensitive_data) else entry.value
                return entry.value
            except CacheEntry.DoesNotExist:
                logger.debug(f"Value for key '{key}' not found in external or database cache.")
                return None
        else:
            logger.debug(f"Value for key '{key}' not found in external cache.")
            return None

    @staticmethod
    def set_cached_value(key: str, value: Any, ttl_seconds: int = 3600, use_db_cache: bool = False):
        """
        Sets a value in the external cache (e.g., Redis).
        Optionally stores in the database cache model as well.
        """
        try:
            # ذخیره در کش خارجی (Redis/Memcached)
            cache.set(key, value, timeout=ttl_seconds)
            logger.debug(f"Value for key '{key}' set in external cache.")

            # اگر نیاز به ذخیره در دیتابیس نیز باشد
            if use_db_cache:
                CacheEntry.set_cached_value(key, value, ttl_seconds)
                logger.debug(f"Value for key '{key}' also set in database cache.")

        except Exception as e:
            logger.error(f"Error setting value in cache for key '{key}': {str(e)}")
            raise CacheError(f"Failed to set cache entry for key '{key}': {str(e)}")

    @staticmethod
    def invalidate_cached_key(key: str, delete_db_entry: bool = True):
        """
        Invalidates (removes) a specific cache key from external cache.
        Optionally removes the corresponding database entry.
        """
        try:
            cache.delete(key)
            logger.info(f"Cache key '{key}' invalidated from external cache.")

            if delete_db_entry:
                from .models import CacheEntry
                CacheEntry.invalidate_cache_key(key) # فرض بر این است که این متد در مدل CacheEntry وجود دارد
                logger.info(f"Corresponding DB cache entry for key '{key}' invalidated if it existed.")
        except Exception as e:
            logger.error(f"Error invalidating cache key '{key}': {str(e)}")
            raise CacheError(f"Failed to invalidate cache entry for key '{key}': {str(e)}")

    @staticmethod
    def bulk_invalidate_cached_keys(keys: List[str], delete_db_entries: bool = True):
        """
        Invalidates multiple cache keys.
        """
        try:
            if not keys:
                logger.info("bulk_invalidate_cached_keys called with empty key list.")
                return

            cache.delete_many(keys)
            logger.info(f"Bulk invalidated {len(keys)} keys from external cache.")

            if delete_db_entries:
                from .models import CacheEntry
                CacheEntry.objects.filter(key__in=keys).delete()
                logger.info(f"Corresponding {len(keys)} DB cache entries invalidated if they existed.")

        except Exception as e:
            logger.error(f"Error bulk invalidating cache keys: {str(e)}")
            raise CacheError(f"Failed to bulk invalidate cache entries: {str(e)}")

# --- سرویس‌های خاص ---
# این سرویس‌ها می‌توانند در فایل‌های جداگانه یا داخل کلاس‌های مجزا در همین فایل قرار گیرند

class AuditService:
    """
    Dedicated service for audit-related operations.
    """
    @staticmethod
    def log_user_action(user, action, target_model_name, target_id, details=None, request=None):
        """
        A convenience method to log user actions using the CoreService.
        """
        return CoreService.log_action(user, action, target_model_name, target_id, details, request)

    @staticmethod
    def get_user_audit_logs(user, action_filter=None, model_filter=None, limit=50):
        """
        Retrieves audit logs for a specific user, with optional filters.
        """
        try:
            queryset = AuditLog.objects.filter(user=user)
            if action_filter:
                queryset = queryset.filter(action__icontains=action_filter)
            if model_filter:
                queryset = queryset.filter(target_model__icontains=model_filter)

            return queryset.order_by('-created_at')[:limit]
        except Exception as e:
            logger.error(f"Error fetching audit logs for user {user.id}: {str(e)}")
            raise AuditLogError(f"Could not fetch audit logs: {str(e)}")

class SecurityService:
    """
    Service class for common security-related operations.
    """
    @staticmethod
    def check_user_ip_against_whitelist(user, client_ip) -> bool:
        """
        Checks if a client IP is allowed based on the user's profile settings.
        This uses the helper function from core.
        """
        try:
            profile = user.profile
            allowed_ips_str = profile.allowed_ips
            if not allowed_ips_str:
                # اگر لیست IPها خالی بود، فرض می‌کنیم همه IPها مجاز هستند
                return True

            allowed_ips_list = [item.strip() for item in allowed_ips_str.split(',') if item.strip()]
            # استفاده از تابع کمکی از helpers (فرض بر این است که تابع وجود دارد)
            # from .helpers import is_ip_in_allowed_list
            # return is_ip_in_allowed_list(client_ip, allowed_ips_list)
            # چون در تست قبلی، این تابع در helpers وجود داشت، اینجا فرض می‌کنیم قابل استفاده است
            # اگر در helpers نبود، باید این منطق را در اینجا پیاده کنیم یا آن را از helpers وارد کنیم
            # مثال ساده: (کامل‌تر در helpers.py)
            from ipaddress import ip_address, ip_network
            client_ip_obj = ip_address(client_ip)
            for allowed_ip_str in allowed_ips_list:
                 if '/' in allowed_ip_str: # CIDR block
                     network = ip_network(allowed_ip_str, strict=False)
                     if client_ip_obj in network:
                         return True
                 else: # Single IP
                     allowed_ip_obj = ip_address(allowed_ip_str)
                     if client_ip_obj == allowed_ip_obj:
                         return True
            return False
        except AttributeError: # اگر پروفایل وجود نداشت
             logger.error(f"User {user.email} does not have a profile for IP whitelist check.")
             return False # یا True بسته به policy - برای امنیت، False
        except Exception as e:
            logger.error(f"Error checking IP for user {user.email}: {str(e)}")
            return False # برای امنیت، در صورت خطا، دسترسی رد می‌شود

    @staticmethod
    def hash_sensitive_data( str) -> str:
        """
        Creates a SHA-256 hash of the input data.
        Useful for hashing sensitive data before logging or storage.
        """
        # فرض بر این است که تابع hash_data در helpers وجود دارد
        # from .helpers import hash_data
        # return hash_data(data)
        import hashlib
        return hashlib.sha256(data.encode()).hexdigest()

    @staticmethod
    def mask_sensitive_data( str, visible_chars: int = 4) -> str:
        """
        Masks sensitive data like API keys or IDs.
        Example: mask_sensitive_data('abc123def456', 3) -> 'abc...456'
        """
        # فرض بر این است که تابع mask_sensitive_data در helpers وجود دارد
        # from .helpers import mask_sensitive_data
        # return mask_sensitive_data(data, visible_chars)
        if len(data) <= 2 * visible_chars:
            return data
        start = data[:visible_chars]
        end = data[-visible_chars:]
        middle = '*' * (len(data) - 2 * visible_chars)
        return f"{start}{middle}{end}"

    @staticmethod
    def generate_secure_token(length: int = 32) -> str:
        """
        Generates a cryptographically secure random token.
        """
        # فرض بر این است که تابع generate_secure_token در helpers وجود دارد
        # from .helpers import generate_secure_token
        # return generate_secure_token(length)
        import secrets
        return secrets.token_urlsafe(length)

# --- سایر سرویس‌های ممکن ---
# مثلاً یک سرویس برای مدیریت کاربران (که ممکن است در اپلیکیشن accounts بماند)
# class UserService:
#     ...

# مثلاً یک سرویس برای مدیریت کش عمومی سیستم
# class SystemCacheService:
#     ...

# مثلاً یک سرویس برای مدیریت تنظیمات عمومی
# class SystemConfigService:
#     ...

logger.info("Core services loaded successfully.")
