# apps/exchanges/tasks.py

from celery import shared_task, current_task
from django.utils import timezone
from django.db import transaction
from decimal import Decimal
import logging
from .models import (
    ExchangeAccount,
    MarketDataCandle,
    OrderHistory,
    # سایر مدل‌های مرتبط
)
from .services import ExchangeService
from .exceptions import (
    ExchangeSyncError,
    DataFetchError,
    OrderExecutionError,
    # سایر استثناهای exchanges
)
from apps.core.exceptions import CoreSystemException # import از core
from apps.core.helpers import mask_sensitive_data # import از core
from apps.core.logging import get_logger # import از core
from apps.core.tasks import log_audit_event_task # import از core
from apps.accounts.models import CustomUser # import از اپلیکیشن دیگر
from apps.bots.models import TradingBot # import از اپلیکیشن دیگر
from apps.exchanges.models import Exchange # import از این اپلیکیشن
from datetime import datetime
import json

logger = get_logger(__name__) # استفاده از لاگر سفارشی core

# --- تاسک‌های مرتبط با همگام‌سازی داده ---
@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def sync_exchange_account_task(self, account_id: int) -> dict:
    """
    Celery task for synchronizing an exchange account's data (balances, orders) asynchronously.
    Implements retry mechanism for transient failures.
    """
    try:
        account = ExchangeAccount.objects.select_related('owner', 'exchange').get(id=account_id)
        service = ExchangeService()
        sync_result = service.sync_exchange_account(account)

        logger.info(f"Sync task completed for account {account.label} (ID: {account_id}).")

        # ثبت در حسابرسی
        log_audit_event_task.delay(
            user_id=account.owner.id,
            action='ACCOUNT_SYNC_SUCCESS',
            target_model_name='ExchangeAccount',
            target_id=account.id,
            details={'result': sync_result},
            request=None # تاسک، درخواستی ندارد
        )

        return sync_result
    except ExchangeAccount.DoesNotExist:
        logger.error(f"ExchangeAccount with id {account_id} does not exist for sync task.")
        # اگر شیء وجود نداشت، دیگر لازم نیست دوباره تلاش شود
        # self.retry(countdown=60, exc=e, throw=False) # نباید دوباره تلاش شود
        raise # یا مدیریت خطا مناسب
    except ExchangeSyncError as e:
        logger.error(f"ExchangeSyncError in sync task for account ID {account_id}: {str(e)}")
        # ثبت خطا در حسابرسی
        log_audit_event_task.delay(
            user_id=account.owner.id, # اگر account قبل از خطا گرفته شد
            action='ACCOUNT_SYNC_ERROR',
            target_model_name='ExchangeAccount',
            target_id=account_id,
            details={'error': str(e)},
            request=None
        )
        raise # Celery retry based on autoretry_for
    except CoreSystemException as e: # اگر سرویس یا مدل core استثنا صادر کرد
        logger.error(f"CoreSystemError in sync task for account ID {account_id}: {str(e)}")
        raise # Celery retry
    except Exception as e:
        logger.error(f"Unexpected error in sync task for account ID {account_id}: {str(e)}")
        # ثبت خطا غیرمنتظره
        log_audit_event_task.delay(
            user_id=account.owner.id if 'account' in locals() else None, # فقط اگر account گرفته شده بود
            action='ACCOUNT_SYNC_ERROR_UNEXPECTED',
            target_model_name='ExchangeAccount',
            target_id=account_id,
            details={'error': str(e)},
            request=None
        )
        raise # Celery retry based on autoretry_for


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 2, 'countdown': 30})
def fetch_market_data_candles_task(self, exchange_code: str, symbol: str, interval: str, limit: int = 100) -> int:
    """
    Celery task for fetching market data candles from an exchange asynchronously.
    This can be scheduled periodically or triggered by demand.
    Uses bulk operations for efficiency.
    """
    try:
        service = ExchangeService()
        # استفاده از سرویس کانکتور یا یک سرویس جداگانه برای دریافت داده
        raw_candles = service.connector_service.fetch_ohlcv(exchange_code, symbol, interval, limit)

        # یافتن صرافی
        exchange = Exchange.objects.get(code__iexact=exchange_code)

        # پردازش و تبدیل داده‌ها
        candle_instances_to_create = []
        for candle_data in raw_candles:
            # تجزیه و تبدیل داده (بسته به فرمت API)
            # [0] Open Time, [1] Open, [2] High, [3] Low, [4] Close, [5] Volume, ...
            open_time_ts = candle_data[0]
            open_time = timezone.make_aware(datetime.fromtimestamp(open_time_ts / 1000)) # تبدیل میلی‌ثانیه
            # تأیید اینکه کندل تاریخ جدیدتری از آخرین کندل ذخیره شده ندارد (یا از طریق یک فیلتر ذخیره کنید)
            # این کار بستگی به نحوه مدیریت داده تاریخی دارد
            # مثلاً:
            # latest_existing_candle_time = MarketDataCandle.objects.filter(exchange=exchange, symbol=symbol, interval=interval).order_by('-open_time').first()
            # if latest_existing_candle_time and open_time <= latest_existing_candle_time.open_time:
            #     continue # این کندل قبلاً وجود داشته است یا قدیمی‌تر است

            candle_instance = MarketDataCandle(
                exchange=exchange,
                symbol=symbol.upper(),
                interval=interval,
                open_time=open_time,
                open=Decimal(str(candle_data[1])),
                high=Decimal(str(candle_data[2])),
                low=Decimal(str(candle_data[3])),
                close=Decimal(str(candle_data[4])),
                volume=Decimal(str(candle_data[5])),
                # سایر فیلدها ...
                close_time=timezone.make_aware(datetime.fromtimestamp(candle_data[6] / 1000)) if candle_data[6] else None,
                quote_asset_volume=Decimal(str(candle_data[7])) if candle_data[7] else Decimal('0'),
                number_of_trades=int(candle_data[8]) if candle_data[8] else 0,
                taker_buy_base_asset_volume=Decimal(str(candle_data[9])) if candle_data[9] else Decimal('0'),
                taker_buy_quote_asset_volume=Decimal(str(candle_data[10])) if candle_data[10] else Decimal('0'),
            )
            candle_instances_to_create.append(candle_instance)

        # ذخیره انبوه داده‌ها
        created_objects = MarketDataCandle.objects.bulk_create(
            candle_instances_to_create,
            update_conflicts=True, # اگر کندل تکراری وجود داشت، بروزرسانی کن (اگر از PostgreSQL استفاده می‌کنید)
            update_fields=['open', 'high', 'low', 'close', 'volume', 'updated_at'], # فیلدهایی که باید در صورت تداخل بروزرسانی شوند
            unique_fields=['exchange', 'symbol', 'interval', 'open_time'] # فیلدهای منحصر به فرد برای تشخیص تداخل
        )
        created_count = len(created_objects) # تعداد ایجاد شده‌ها

        logger.info(f"Fetched and bulk stored {created_count} candles for {symbol} on {exchange_code} ({interval}) via task.")

        return created_count

    except Exchange.DoesNotExist:
        logger.error(f"Exchange with code {exchange_code} does not exist for fetch candles task.")
        raise # این خطا باید به صورت دستی مدیریت شود، نه با retry
    except DataFetchError as e:
        logger.error(f"DataFetchError in fetch candles task for {symbol} on {exchange_code} ({interval}): {str(e)}")
        raise # Celery retry based on autoretry_for
    except CoreSystemException as e:
        logger.error(f"CoreSystemError in fetch candles task: {str(e)}")
        raise # Celery retry
    except Exception as e:
        logger.error(f"Unexpected error in fetch candles task for {symbol} on {exchange_code} ({interval}): {str(e)}")
        # ثبت خطا در حسابرسی
        log_audit_event_task.delay(
            user_id=None, # این تاسک ممکن است توسط یک عامل یا سیستم انجام شود
            action='CANDLE_FETCH_ERROR',
            target_model_name='MarketDataCandle',
            target_id=None, # نمی‌توان ID را تعیین کرد، زیرا هنوز ذخیره نشده است
            details={'exchange': exchange_code, 'symbol': symbol, 'interval': interval, 'error': str(e)},
            request=None
        )
        raise # Celery retry based on autoretry_for


# --- تاسک‌های مرتبط با معاملات ---
@shared_task(bind=True)
def place_order_task(self, account_id: int, bot_id: int, order_params: dict) -> dict:
    """
    Celery task for placing an order on the exchange asynchronously.
    """
    try:
        from apps.bots.models import TradingBot # import درون تابع برای جلوگیری از حلقه
        account = ExchangeAccount.objects.select_related('owner', 'exchange').get(id=account_id)
        bot = TradingBot.objects.get(id=bot_id, owner=account.owner) # اطمینان از اینکه بات متعلق به مالک حساب است

        service = ExchangeService()
        order_response = service.place_order(account, bot, order_params)

        logger.info(f"Order placed successfully via task for bot {bot.name} on account {account.label}.")

        # ثبت در حسابرسی
        log_audit_event_task.delay(
            user_id=account.owner.id,
            action='ORDER_PLACED',
            target_model_name='OrderHistory',
            target_id=order_response.get('order_id'), # اگر ID سفارش در پاسخ وجود داشت
            details={'order_params': mask_sensitive_data(json.dumps(order_params)), 'response': order_response},
            request=None
        )

        return order_response
    except (ExchangeAccount.DoesNotExist, TradingBot.DoesNotExist) as e:
        logger.error(f"Object does not exist for place order task: {str(e)}")
        raise # این خطاها باید به صورت دستی مدیریت شوند
    except OrderExecutionError as e:
        logger.error(f"OrderExecutionError in place order task: {str(e)}")
        # ثبت خطا در حسابرسی
        log_audit_event_task.delay(
            user_id=account.owner.id if 'account' in locals() else None,
            action='ORDER_PLACEMENT_ERROR',
            target_model_name='ExchangeAccount',
            target_id=account_id,
            details={'bot_id': bot_id, 'order_params': mask_sensitive_data(json.dumps(order_params)), 'error': str(e)},
            request=None
        )
        raise # یا مدیریت خطا مناسب و احتمالاً ارسال اعلان
    except CoreSystemException as e:
        logger.error(f"CoreSystemError in place order task: {str(e)}")
        raise # Celery retry
    except Exception as e:
        logger.error(f"Unexpected error in place order task: {str(e)}")
        log_audit_event_task.delay(
            user_id=account.owner.id if 'account' in locals() else None,
            action='ORDER_PLACEMENT_ERROR_UNEXPECTED',
            target_model_name='ExchangeAccount',
            target_id=account_id,
            details={'bot_id': bot_id, 'order_params': mask_sensitive_data(json.dumps(order_params)), 'error': str(e)},
            request=None
        )
        raise # Celery retry based on autoretry_for if applicable


@shared_task(bind=True)
def cancel_order_task(self, account_id: int, order_id: str) -> dict:
    """
    Celery task for canceling an order on the exchange asynchronously.
    """
    try:
        account = ExchangeAccount.objects.select_related('owner', 'exchange').get(id=account_id)

        service = ExchangeService()
        cancel_response = service.cancel_order(account, order_id)

        logger.info(f"Order {order_id} canceled successfully via task on account {account.label}.")

        # ثبت در حسابرسی
        log_audit_event_task.delay(
            user_id=account.owner.id,
            action='ORDER_CANCELED',
            target_model_name='OrderHistory',
            target_id=order_id,
            details={'response': cancel_response},
            request=None
        )

        return cancel_response
    except ExchangeAccount.DoesNotExist:
        logger.error(f"ExchangeAccount with id {account_id} does not exist for cancel order task.")
        raise
    except Exception as e:
        logger.error(f"Error canceling order {order_id} via task: {str(e)}")
        log_audit_event_task.delay(
            user_id=account.owner.id if 'account' in locals() else None,
            action='ORDER_CANCEL_ERROR',
            target_model_name='ExchangeAccount',
            target_id=account_id,
            details={'order_id': order_id, 'error': str(e)},
            request=None
        )
        raise # Celery retry based on autoretry_for if applicable


# --- تاسک‌های مرتبط با کش ---
@shared_task
def invalidate_cache_for_instrument_task(symbol: str, exchange_code: str):
    """
    Celery task for invalidating cached data related to a specific instrument on an exchange.
    """
    from apps.core.cache import CacheService # import درون تابع
    # مثال: حذف کش کندل‌های یک نماد
    cache_key_pattern = f"candle_data_{exchange_code.lower()}_{symbol.lower()}_*" # الگوی کلید کش
    # این الگوی کلید را نمی‌توان مستقیماً در Django Cache استفاده کرد
    # ممکن است نیاز به استفاده از Redis مستقیم داشته باشید
    # import redis
    # r = redis.Redis.from_url(settings.REDIS_URL)
    # keys_to_delete = r.keys(cache_key_pattern)
    # if keys_to_delete:
    #     r.delete(*keys_to_delete)
    #     logger.info(f"Invalidated {len(keys_to_delete)} cache keys matching pattern '{cache_key_pattern}'.")
    # یا فقط حذف ورودی مربوطه از مدل CacheEntry در پایگاه داده
    from apps.core.models import CacheEntry
    CacheEntry.objects.filter(key__startswith=f"candle_data_{exchange_code.lower()}_{symbol.lower()}").delete()
    logger.info(f"Invalidated DB cache entries for instrument {symbol} on exchange {exchange_code}.")


# --- تاسک‌های مرتبط با امنیت ---
@shared_task
def log_security_event_task(user_id: int, event_type: str, details: dict, ip_address: str = None):
    """
    Celery task for logging security-related events asynchronously.
    """
    try:
        from apps.accounts.models import CustomUser
        user = CustomUser.objects.get(id=user_id) if user_id else None
        AuditLog.objects.create(
            user=user,
            action=f"SECURITY_{event_type.upper()}",
            target_model="SecurityEvent",
            target_id=None,
            details=details,
            ip_address=ip_address,
        )
        logger.info(f"Security event '{event_type}' logged asynchronously for user {user.email if user else 'Anonymous'}.")
    except CustomUser.DoesNotExist:
        logger.error(f"User with id {user_id} does not exist for security event log task.")
        # یا فقط لاگ کنید و ادامه دهید اگر user_id اختیاری است
    except Exception as e:
        logger.error(f"Error logging security event asynchronously: {str(e)}")
        # ممکن است بخواهید دوباره تلاش کنید یا خطایی را گزارش دهید
        raise # یا مدیریت خطا


# --- تاسک‌های مرتبط با کاربر ---
@shared_task
def update_user_instrument_access_cache_task(user_id: int):
    """
    Celery task for updating a user's instrument access permissions in cache.
    """
    try:
        user = CustomUser.objects.get(id=user_id)
        # منطقی برای گرفتن لیست نمادهای مجاز کاربر و ذخیره در کش
        # مثلاً:
        # allowed_instruments = user.exchange_accounts.filter(is_active=True).values_list('instrument_mappings__instrument__symbol', flat=True)
        # cache_key = f"user_{user.id}_allowed_instruments"
        # cache.set(cache_key, list(allowed_instruments), timeout=3600) # 1 hour
        logger.info(f"User instrument access cache updated for user {user.email}.")
    except CustomUser.DoesNotExist:
        logger.error(f"User with id {user_id} does not exist for cache update task.")
        raise
    except Exception as e:
        logger.error(f"Error updating user instrument access cache for user ID {user_id}: {str(e)}")
        raise # یا مدیریت خطا


# --- تاسک‌های مرتبط با سیگنال‌ها ---
# مثال: تاسکی که هنگام ایجاد یا بروزرسانی یک حساب صرافی، کش مربوطه را بروز می‌کند
@shared_task
def invalidate_account_related_cache_task(account_id: int):
    """
    Celery task to invalidate cache entries related to a specific exchange account.
    e.g., balances, recent orders.
    """
    try:
        account = ExchangeAccount.objects.get(id=account_id)
        # حذف کش مربوط به موجودی‌ها
        # cache.delete(f"balances_for_account_{account_id}")
        # حذف کش مربوط به سفارشات اخیر
        # cache.delete(f"recent_orders_for_account_{account_id}")
        # یا حذف ورودی‌های مربوطه از مدل CacheEntry
        from apps.core.models import CacheEntry
        CacheEntry.objects.filter(key__contains=f"account_{account_id}").delete()
        logger.info(f"Cache invalidated for account {account.label} (ID: {account_id}).")
    except ExchangeAccount.DoesNotExist:
        logger.error(f"Account with id {account_id} does not exist for cache invalidation task.")
        raise
    except Exception as e:
        logger.error(f"Error invalidating cache for account ID {account_id}: {str(e)}")
        raise


# --- سایر تاسک‌های مرتبط ---
# می‌توانید تاسک‌های دیگری مانند:
# - cleanup_old_logs_task
# - sync_all_accounts_periodically_task
# - validate_exchange_credentials_task
# - send_alerts_if_credentials_expired_task
# - update_exchange_specific_limits_task
# را نیز در این فایل اضافه کنید.

logger.info("Exchanges tasks loaded successfully.")
