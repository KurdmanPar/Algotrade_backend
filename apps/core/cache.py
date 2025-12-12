# apps/core/cache.py

import logging
from typing import Any, Optional, Union
from django.core.cache import cache
from django.utils import timezone
from decimal import Decimal
import json
import hashlib
import secrets
from .models import CacheEntry # فرض بر این است که مدل CacheEntry در core یا instruments قرار دارد

logger = logging.getLogger(__name__)

# --- کلاس‌های کمکی کش ---

class CacheService:
    """
    Service class for handling common caching operations using both external cache (e.g., Redis)
    and potentially an internal database cache model (CacheEntry).
    This service abstracts the caching logic.
    """
    @staticmethod
    def get_cached_value(key: str, use_db_fallback: bool = True) -> Optional[Any]:
        """
        Retrieves a value from the external cache (e.g., Redis).
        Optionally falls back to the CacheEntry model if not found externally.
        """
        # اول از کش خارجی (Redis/Memcached)
        cached_val = cache.get(key)
        if cached_val is not None:
            logger.debug(f"Value for key '{key}' retrieved from external cache.")
            return cached_val

        # اگر در کش خارجی نبود و فبل‌بک مجاز است
        if use_db_fallback:
            try:
                from apps.core.models import CacheEntry # import داخل تابع برای جلوگیری از حلقه
                db_entry = CacheEntry.objects.get(key=key)
                if db_entry.is_expired():
                    logger.info(f"DB cache entry for key '{key}' is expired. Deleting.")
                    db_entry.delete()
                    return None
                logger.debug(f"Value for key '{key}' retrieved from database cache.")
                # احتمالاً نیاز به دیسrialize داده داشته باشیم اگر JSON ذخیره شده بود
                # return db_entry.value # اگر مقدار خام ذخیره شده باشد
                return json.loads(db_entry.value) # اگر مقدار JSON شده باشد
            except CacheEntry.DoesNotExist:
                logger.debug(f"Value for key '{key}' not found in external or database cache.")
                return None
        else:
            logger.debug(f"Value for key '{key}' not found in external cache.")
            return None

    @staticmethod
    def set_cached_value(key: str, value: Any, ttl_seconds: int = 3600, use_db_cache: bool = False, serialize_value: bool = True):
        """
        Sets a value in the external cache.
        Optionally stores in the CacheEntry model if use_db_cache is True.
        """
        # ذخیره در کش خارجی (Redis/Memcached)
        # اگر مقدار یک شیء پایتونی پیچیده است، باید قبل از کش کردن serialize شود (مثلاً به JSON)
        cache_value = json.dumps(value) if serialize_value else value
        cache.set(key, cache_value, timeout=ttl_seconds)
        logger.debug(f"Value for key '{key}' set in external cache.")

        # اگر نیاز به ذخیره در دیتابیس نیز باشد
        if use_db_cache:
            try:
                from apps.core.models import CacheEntry
                expires_at = timezone.now() + timezone.timedelta(seconds=ttl_seconds) if ttl_seconds else None
                # اگر مقدار serialize شد، همان رشته JSON ذخیره می‌شود
                CacheEntry.objects.update_or_create(
                    key=key,
                    defaults={
                        'value': cache_value, # ذخیره مقدار serial شده یا خام
                        'expires_at': expires_at
                    }
                )
                logger.debug(f"Value for key '{key}' also set in database cache.")
            except Exception as e:
                logger.error(f"Error setting value in database cache for key '{key}': {str(e)}")
                # مدیریت خطا مناسب (مثلاً فقط لاگ کردن یا ایجاد یک استثنا)

    @staticmethod
    def invalidate_cached_value(key: str, delete_db_entry: bool = True):
        """
        Invalidates (removes) a specific value from the external cache.
        Optionally removes the corresponding database entry.
        """
        cache.delete(key)
        logger.debug(f"Value for key '{key}' invalidated from external cache.")

        if delete_db_entry:
            from apps.core.models import CacheEntry
            deleted_count, _ = CacheEntry.objects.filter(key=key).delete()
            if deleted_count > 0:
                 logger.debug(f"Corresponding DB cache entry for key '{key}' deleted.")
            else:
                 logger.debug(f"No corresponding DB cache entry found for key '{key}' to delete.")

    @staticmethod
    def bulk_invalidate_cached_values(keys: list[str], delete_db_entries: bool = True):
        """
        Invalidates multiple cache keys at once.
        Optionally removes the corresponding database entries.
        """
        if not keys:
            return

        cache.delete_many(keys)
        logger.debug(f"{len(keys)} values invalidated from external cache.")

        if delete_db_entries:
            from apps.core.models import CacheEntry
            deleted_count, _ = CacheEntry.objects.filter(key__in=keys).delete()
            logger.debug(f"{deleted_count} corresponding DB cache entries deleted.")

    @staticmethod
    def get_or_set_with_function(key: str, func, ttl: int = 3600, *args, **kwargs):
        """
        Retrieves a value from cache, or if not found, executes a function,
        caches its result, and returns the result.
        This is a common pattern to avoid repeated expensive computations or queries.
        """
        cached_value = CacheService.get_cached_value(key)
        if cached_value is not None:
            return cached_value

        # اگر در کش نبود، تابع را اجرا کن
        logger.info(f"Cache miss for key '{key}'. Executing function.")
        result = func(*args, **kwargs)

        # نتیجه را کش کن
        CacheService.set_cached_value(key, result, ttl_seconds=ttl)
        logger.info(f"Computed value for key '{key}' cached successfully.")
        return result

    # --- مثال: کش کردن نتیجه یک کوئری ---
    @staticmethod
    def get_instruments_for_exchange_cached(exchange_code: str, ttl: int = 300) -> list:
        """
        Retrieves instruments for an exchange from cache or DB.
        """
        cache_key = f"instruments_for_exchange_{exchange_code.lower()}"
        cached_result = CacheService.get_or_set_with_function(
            key=cache_key,
            func=lambda: list(Instrument.objects.filter(exchange_mappings__exchange__code__iexact=exchange_code, exchange_mappings__is_active=True).values_list('symbol', flat=True)),
            ttl=ttl
        )
        return cached_result

    # --- مثال: کش کردن نتیجه یک محاسبه ---
    @staticmethod
    def get_vwap_for_instrument_cached(instrument_id: int, start_time, end_time, ttl: int = 60) -> Optional[Decimal]:
        """
        Retrieves pre-calculated VWAP for an instrument in a time range from cache or calculates it.
        """
        cache_key = f"vwap_{instrument_id}_{start_time.timestamp()}_{end_time.timestamp()}"
        cached_vwap = CacheService.get_or_set_with_function(
            key=cache_key,
            func=lambda: calculate_vwap_logic(instrument_id, start_time, end_time), # فرض بر این است که این تابع وجود دارد
            ttl=ttl
        )
        return cached_vwap

# --- توابع کمکی ---
def generate_cache_key(prefix: str, identifier: str, suffix: str = "") -> str:
    """
    Generates a standard cache key format.
    Example: generate_cache_key('instrument', 'BTCUSDT', '1m_ohlcv') -> 'instrument_BTCUSDT_1m_ohlcv'
    """
    parts = [prefix, identifier]
    if suffix:
        parts.append(suffix)
    return "_".join(parts)

def invalidate_cache_for_instrument(symbol: str):
    """
    Invalidates all cache entries related to a specific instrument symbol.
    This is useful when instrument data changes significantly.
    """
    # مثال ساده: فرض کنید کلیدهای کش ما با نام نماد شروع می‌شوند
    # این کار معمولاً در Redis با استفاده از الگو (pattern) انجام می‌شود
    # چون Django cache backend ممکن است این قابلیت را نداشته باشد، فقط از طریق DB Cache انجام می‌دهیم
    # یا کلیدهای مرتبط را به صورت دستی ایجاد کرده و اینجا حذف می‌کنیم
    # مثلاً:
    related_keys = [
        f"instruments_for_exchange_binance_{symbol.lower()}",
        f"instruments_for_exchange_coinbase_{symbol.lower()}",
        # ... سایر کلیدهایی که ممکن است به نماد وابسته باشند
    ]
    CacheService.bulk_invalidate_cached_values(related_keys)
    logger.info(f"All cache entries related to instrument '{symbol}' invalidated.")

def invalidate_cache_for_strategy(strategy_id: str):
    """
    Invalidates cache entries related to a specific strategy.
    """
    # مشابه بالا
    related_keys = [
        f"strategy_config_{strategy_id}",
        f"strategy_performance_{strategy_id}",
        # ...
    ]
    CacheService.bulk_invalidate_cached_values(related_keys)
    logger.info(f"All cache entries related to strategy '{strategy_id}' invalidated.")

# --- کلاس‌های کش مبتنی بر مدل ---
# اگر از مدل CacheEntry در پایگاه داده استفاده می‌کنید، می‌توانید منیجرها و کوئری‌ست‌های مربوطه را در apps/core/managers.py یا همینجا تعریف کنید.
# مثلاً:
# from django.db import models
# class CacheEntryQuerySet(models.QuerySet):
#     def expired(self):
#         now = timezone.now()
#         return self.filter(expires_at__lt=now, is_active=True)
#
#     def active(self):
#         now = timezone.now()
#         return self.filter(expires_at__gte=now, is_active=True).union(
#             self.filter(expires_at__isnull=True, is_active=True) # کش‌های بدون انقضا
#         )
#
# class CacheEntryManager(models.Manager):
#     def get_queryset(self):
#         return CacheEntryQuerySet(self.model, using=self._db)
#
#     def get_cached_value(self, key: str):
#         try:
#             entry = self.active().get(key=key)
#             # Deserialize if necessary
#             return json.loads(entry.value)
#         except CacheEntry.DoesNotExist:
#             return None
#
#     def set_cached_value(self, key: str, value: Any, ttl_seconds: int = None):
#         expires_at = timezone.now() + timezone.timedelta(seconds=ttl_seconds) if ttl_seconds else None
#         entry, created = self.update_or_create(
#             key=key,
#             defaults={
#                 'value': json.dumps(value), # Serialize
#                 'expires_at': expires_at,
#                 'is_active': True
#             }
#         )
#         return entry
#
# # و سپس در مدل CacheEntry:
# # objects = CacheEntryManager()

logger.info("Cache service components loaded.")
