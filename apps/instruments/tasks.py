# apps/instruments/tasks.py

from celery import shared_task
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.translation import gettext_lazy as _
import logging
import json

from apps.core.exceptions import CoreTaskError
from .models import (
    Instrument,
    InstrumentExchangeMap,
    IndicatorTemplate,
    PriceActionPattern,
    SmartMoneyConcept,
    AIMetric,
    InstrumentWatchlist,
)
from .services import InstrumentService, IndicatorService, WatchlistService
from .exceptions import (
    InstrumentSyncError,
    DataFetchError,
    DataValidationError,
    WatchlistError,
    WatchlistOwnershipError,
)
from apps.connectors.service import ConnectorService # فرض بر این است که این سرویس وجود دارد
from apps.core.logging import get_logger # فرض بر این است که یک سیستم لاگ مرکزی دارید

logger = get_logger(__name__) # استفاده از سیستم لاگ مرکزی

@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def sync_instrument_details_from_exchange_task(self, instrument_id: int, exchange_id: int):
    """
    Celery task for syncing specific instrument details from an exchange.
    Uses the InstrumentService for the core logic.
    Implements retry mechanism for transient failures.
    """
    try:
        InstrumentService.sync_instrument_details_from_exchange(instrument_id, exchange_id)
        logger.info(f"Successfully synced details for instrument ID {instrument_id} on exchange ID {exchange_id}.")
    except (Instrument.DoesNotExist, InstrumentExchangeMap.DoesNotExist) as e:
        logger.error(f"Object not found during sync task for instrument {instrument_id}, exchange {exchange_id}: {str(e)}")
        # اگر شیء وجود نداشته باشد، دیگر لازم نیست دوباره تلاش شود
        # self.retry(countdown=60, exc=e, throw=False) # نباید دوباره تلاش شود
        raise # یا فقط لاگ کنید و خارج شوید
    except (DataFetchError, DataValidationError) as e:
        # خطاها ممکن است قابل تلاش مجدد باشند
        logger.warning(f"Sync task failed for instrument {instrument_id}, exchange {exchange_id} due to data issue: {str(e)}. Retrying...")
        raise # Celery retry
    except Exception as e:
        logger.error(f"Unexpected error in sync task for instrument {instrument_id}, exchange {exchange_id}: {str(e)}")
        raise # Celery retry based on autoretry_for


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 2, 'countdown': 30})
def fetch_and_store_historical_data_task(self, config_id: int):
    """
    Task for fetching historical market data based on a MarketDataConfig and storing it.
    This would typically interact with the market_data app's models and services.
    """
    try:
        from apps.market_data.services import MarketDataService # Import داخل تابع برای جلوگیری از حلقه
        from apps.market_data.models import MarketDataConfig

        config = MarketDataConfig.objects.select_related('instrument', 'data_source').get(id=config_id)

        logger.info(f"Starting historical sync for config {config_id} ({config.instrument.symbol} on {config.data_source.name}).")

        # استفاده از سرویس MarketData برای انجام کار
        MarketDataService.trigger_historical_sync(config)

        logger.info(f"Historical sync completed for config {config_id}.")
    except MarketDataConfig.DoesNotExist:
        logger.error(f"MarketDataConfig with ID {config_id} not found for historical sync task.")
        # ممکن است بخواهید این را لاگ کنید و خارج شوید، نه اینکه دوباره تلاش کنید
        # raise ...
    except Exception as e:
        logger.error(f"Error in historical sync task for config {config_id}: {str(e)}")
        # ممکن است نیاز به مدیریت خطا و تلاش مجدد داشته باشد
        raise # یا منطق تلاش مجدد خود را اضافه کنید


@shared_task
def send_instrument_notification_task(user_id: int, instrument_symbol: str, message: str):
    """
    Sends a notification about an instrument event to a specific user.
    """
    try:
        # فرض کنید یک مدل User یا تابعی برای گرفتن کاربر داریم
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(id=user_id)

        subject = f"Instrument Notification: {instrument_symbol}"
        context = {
            'user': user,
            'instrument_symbol': instrument_symbol,
            'message': message,
            'site_name': getattr(settings, 'SITE_NAME', 'Trading Platform'),
        }

        text_content = render_to_string('instruments/notifications/instrument_notification.txt', context)
        html_content = render_to_string('instruments/notifications/instrument_notification.html', context)

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        logger.info(f"Notification email sent to user {user.email} for instrument {instrument_symbol}.")
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} does not exist for notification task.")
    except Exception as e:
        logger.error(f"Failed to send notification email task for user {user_id}, instrument {instrument_symbol}: {str(e)}")
        # ممکن است بخواهید دوباره تلاش کنید یا خطایی را گزارش دهید


@shared_task
def cleanup_expired_watchlists_task():
    """
    Periodic task (scheduled via Celery Beat) to delete or archive expired watchlists.
    """
    try:
        from django.utils import timezone
        from datetime import timedelta
        # فرض بر این است که مدل InstrumentWatchlist فیلدی مانند 'expires_at' دارد
        expired_watchlists = InstrumentWatchlist.objects.filter(expires_at__lt=timezone.now(), is_active=True)

        count = 0
        for wl in expired_watchlists:
            # می‌توانید فقط غیرفعال کنید یا کاملاً حذف کنید
            wl.is_active = False
            wl.save(update_fields=['is_active'])
            # wl.delete() # اگر حذف کامل مدنظر است
            count += 1

        logger.info(f"Cleaned up {count} expired watchlists.")
    except Exception as e:
        logger.error(f"Error in cleanup_expired_watchlists_task: {str(e)}")
        raise # یا فقط لاگ کنید


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 1})
def process_instrument_metadata_update_task(self, instrument_id: int, metadata_update_ dict):
    """
    Asynchronously updates the metadata JSON field of an instrument.
    Useful for bulk updates or updates triggered by external events/data feeds.
    """
    try:
        logger.info(f"Task started for updating metadata of instrument ID {instrument_id}.")
        updated_instrument = InstrumentService.update_instrument_metadata(instrument_id, metadata_update_dict)
        logger.info(f"Successfully updated metadata for instrument ID {instrument_id}.")
        # می‌توانید یک پاسخ یا ID شیء به‌روزرسانی شده برگردانید
        return updated_instrument.id
    except Instrument.DoesNotExist:
        logger.error(f"Task failed: Instrument with ID {instrument_id} not found for metadata update.")
        # اگر شیء وجود نداشت، دیگر لازم نیست تلاش مجدد انجام شود.
        # self.retry(countdown=60, exc=e, throw=False) # این خط باید حذف یا شرطی شود
        return None # یا مثلاً یک کد خطا
    except Exception as e:
        logger.error(f"Task failed with unexpected error for instrument ID {instrument_id}: {str(e)}")
        # این تاسک ممکن است نیاز به تلاش مجدد نداشته باشد یا فقط یک بار
        # این قبلاً در autoretry_for مشخص شده است
        raise # Celery will handle retry based on decorator


@shared_task
def aggregate_instrument_statistics_task(instrument_id: int, period: str = '24h'):
    """
    Task to calculate and store aggregated statistics for an instrument over a given period.
    This could involve querying market data, calculating metrics like volatility, volume spikes, etc.
    """
    try:
        from apps.market_data.models import MarketDataSnapshot # Import داخل تابع
        from django.db.models import Avg, Sum, Max, Min, Count
        from datetime import timedelta

        instrument = Instrument.objects.get(id=instrument_id)
        now = timezone.now()
        if period == '24h':
            start_time = now - timedelta(hours=24)
        elif period == '7d':
            start_time = now - timedelta(days=7)
        elif period == '1mo':
            start_time = now - timedelta(days=30)
        else:
            logger.warning(f"Unknown period '{period}' for statistics aggregation task for instrument {instrument.id}. Skipping.")
            return

        # محاسبات آگریگیت
        snapshots = MarketDataSnapshot.objects.filter(
            instrument=instrument,
            timestamp__gte=start_time,
            timestamp__lte=now
        )

        stats = snapshots.aggregate(
            avg_price=Avg('close_price'),
            total_volume=Sum('volume'),
            high_price=Max('high_price'),
            low_price=Min('low_price'),
            num_snapshots=Count('id')
        )

        # فرض بر این است که یک مدل یا فیلد اختصاصی برای ذخیره این آمار وجود دارد
        # مثلاً InstrumentStatistics یا یک فیلد JSON در خود Instrument
        # instrument.statistics[f'{period}_stats'] = stats
        # instrument.save(update_fields=['statistics'])

        logger.info(f"Aggregated {period} statistics for instrument {instrument.symbol}: {stats}")

    except Instrument.DoesNotExist:
        logger.error(f"Cannot aggregate stats: Instrument with ID {instrument_id} not found.")
    except Exception as e:
        logger.error(f"Error aggregating stats for instrument ID {instrument_id} and period {period}: {str(e)}")
        raise # یا مدیریت خطا


# --- تاسک‌های مرتبط با Indicator ---
@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 2, 'countdown': 10})
def calculate_indicator_for_instrument_task(self, indicator_template_id: int, instrument_id: int, data_range: str = 'recent'):
    """
    Task to calculate an indicator based on a template for a specific instrument.
    This would typically fetch recent price data and apply the indicator's logic.
    """
    try:
        from apps.market_data.services import MarketDataService # فرض بر این است که وجود دارد
        from apps.market_data.models import MarketDataSnapshot # فرض بر این است که وجود دارد

        template = IndicatorTemplate.objects.select_related('indicator').get(id=indicator_template_id)
        instrument = Instrument.objects.get(id=instrument_id)

        logger.info(f"Calculating indicator '{template.indicator.name}' for instrument '{instrument.symbol}' using template '{template.name}'.")

        # 1. گرفتن داده‌های قیمت
        # مثلاً گرفتن آخرین 100 کندل
        num_periods = 100
        if data_range == 'recent':
            price_data = MarketDataSnapshot.objects.filter(
                instrument=instrument
            ).order_by('-timestamp')[:num_periods]
        else:
             # می‌توانید بازه زمانی دلخواه دیگری را نیز پشتیبانی کنید
             logger.warning(f"Data range '{data_range}' not fully implemented in task. Using 'recent'.")
             price_data = MarketDataSnapshot.objects.filter(
                 instrument=instrument
             ).order_by('-timestamp')[:num_periods]

        if not price_data.exists():
             logger.warning(f"No price data found for instrument {instrument.symbol} to calculate indicator '{template.indicator.name}'.")
             return None

        # تبدیل QuerySet به لیست یا دیکشنری مناسب برای محاسبات
        ohlcv_list = [(s.timestamp, s.open_price, s.high_price, s.low_price, s.close_price, s.volume) for s in price_data]

        # 2. استفاده از منطق محاسباتی اندیکاتور
        # این بخش بستگی به این دارد که چگونه منطق اندیکاتورها پیاده‌سازی شده‌اند
        # فرض بر این است که یک سرویس یا کتابخانه خارجی وجود دارد که این کار را انجام می‌دهد
        # مثلاً:
        # from apps.analytics.indicator_calculator import run_calculation
        # result = run_calculation(template.indicator.code, ohlcv_list, template.parameters)

        # 3. ذخیره نتیجه (مثلاً در یک مدل جدید یا کش)
        # from apps.analytics.models import IndicatorResult
        # IndicatorResult.objects.create(
        #     template=template,
        #     instrument=instrument,
        #     calculated_at=timezone.now(),
        #     result_data=result # ممکن است JSON یا یک فیلد دیگر باشد
        # )

        logger.info(f"Calculated indicator '{template.indicator.name}' for instrument '{instrument.symbol}' successfully.")
        # return result # اگر نیاز به بازگرداندن خروجی محاسبه است

    except IndicatorTemplate.DoesNotExist:
        logger.error(f"IndicatorTemplate with ID {indicator_template_id} not found for calculation task.")
        return None
    except Instrument.DoesNotExist:
        logger.error(f"Instrument with ID {instrument_id} not found for indicator calculation task.")
        return None
    except Exception as e:
        logger.error(f"Error calculating indicator for template ID {indicator_template_id} and instrument ID {instrument_id}: {str(e)}")
        raise # Celery retry


# --- تاسک‌های مرتبط با Watchlist ---
@shared_task
def send_watchlist_summary_email_task(watchlist_id: int, user_id: int):
    """
    Sends a periodic summary email of instruments in a watchlist.
    """
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.get(id=user_id)
        watchlist = InstrumentWatchlist.objects.prefetch_related('instruments').get(id=watchlist_id)

        subject = f"Watchlist Summary: {watchlist.name}"
        context = {
            'user': user,
            'watchlist': watchlist,
            'instruments': watchlist.instruments.all(), # یا داده‌های خاصی از اینسترومنت‌ها
            'site_name': getattr(settings, 'SITE_NAME', 'Trading Platform'),
        }

        text_content = render_to_string('instruments/emails/watchlist_summary.txt', context)
        html_content = render_to_string('instruments/emails/watchlist_summary.html', context)

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        logger.info(f"Summary email sent for watchlist '{watchlist.name}' to user {user.email}.")
    except (InstrumentWatchlist.DoesNotExist, User.DoesNotExist) as e:
        logger.error(f"Object not found for watchlist summary email task: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to send watchlist summary email for watchlist ID {watchlist_id}, user ID {user_id}: {str(e)}")
        raise # یا مدیریت خطا


# --- سایر تاسک‌های مرتبط ---
# می‌توانید تاسک‌های دیگری مانند:
# - sync_all_instruments_for_exchange_task
# - recalculate_all_indicators_task
# - validate_instrument_data_task
# - cleanup_stale_data_task
# - generate_market_report_task
# - send_smart_money_alerts_task
# - update_aimetric_values_task
# را نیز اضافه کنید.
