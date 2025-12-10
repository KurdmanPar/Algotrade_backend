# apps/exchanges/tasks.py

from celery import shared_task
import logging
from django.utils import timezone
from .models import ExchangeAccount, MarketDataCandle
from .services import ExchangeService # فرض بر این است که این سرویس وجود دارد
from .exceptions import ExchangeSyncError, DataFetchError # فرض بر این است که این استثناها وجود دارند
from apps.market_data.service import MarketDataService # فرض بر این است که این سرویس وجود دارند

logger = logging.getLogger(__name__)

@shared_task
def sync_exchange_account_task(account_id: int) -> dict:
    """
    Celery task for synchronizing an exchange account's data (balances, orders) asynchronously.
    """
    try:
        account = ExchangeAccount.objects.get(id=account_id)
        service = ExchangeService()
        sync_result = service.sync_exchange_account(account)
        logger.info(f"Sync task completed for account {account.label} (ID: {account_id}).")
        return sync_result
    except ExchangeAccount.DoesNotExist:
        logger.error(f"ExchangeAccount with id {account_id} does not exist for sync task.")
        raise
    except ExchangeSyncError as e:
        logger.error(f"ExchangeSyncError in sync task for account ID {account_id}: {str(e)}")
        raise # یا مدیریت خطا و تلاش مجدد
    except Exception as e:
        logger.error(f"Unexpected error in sync task for account ID {account_id}: {str(e)}")
        raise

@shared_task
def fetch_market_data_candles_task(exchange_code: str, symbol: str, interval: str, limit: int = 100) -> int:
    """
    Celery task for fetching market data candles from an exchange asynchronously.
    This can be scheduled periodically or triggered by demand.
    """
    try:
        service = ExchangeService()
        # استفاده از سرویس کانکتور یا یک سرویس جداگانه برای دریافت داده
        raw_candles = service.connector_service.fetch_ohlcv(exchange_code, symbol, interval, limit)
        # ذخیره داده در مدل MarketDataCandle
        # توجه: این بخش نیازمند نگاشت صحیح داده‌ها از ساختار API به مدل مربوطه است
        created_count = 0
        for candle_data in raw_candles:
            # تبدیل timestamp (اگر لازم باشد)
            # open_time = timezone.make_aware(datetime.fromtimestamp(candle_data[0] / 1000))
            # ... سایر فیلدها ...
            # فرض بر این است که candle_data یک لیست یا دیکشنری با فیلدهای صحیح است
            # ممکن است نیاز به اعتبارسنجی یا پردازش بیشتری داشته باشد
            exchange = Exchange.objects.get(code__iexact=exchange_code)
            obj, created = MarketDataCandle.objects.update_or_create(
                exchange=exchange,
                symbol=symbol.upper(),
                interval=interval,
                open_time=timezone.make_aware(datetime.fromtimestamp(candle_data[0] / 1000)),
                defaults={
                    'open': Decimal(str(candle_data[1])),
                    'high': Decimal(str(candle_data[2])),
                    'low': Decimal(str(candle_data[3])),
                    'close': Decimal(str(candle_data[4])),
                    'volume': Decimal(str(candle_data[5])),
                    'close_time': timezone.make_aware(datetime.fromtimestamp(candle_data[6] / 1000)),
                    'quote_asset_volume': Decimal(str(candle_data[7])),
                    'number_of_trades': int(candle_data[8]),
                    'taker_buy_base_asset_volume': Decimal(str(candle_data[9])),
                    'taker_buy_quote_asset_volume': Decimal(str(candle_data[10])),
                }
            )
            if created:
                created_count += 1

        logger.info(f"Fetched and stored {created_count} new candles for {symbol} on {exchange_code} ({interval}) via task.")
        return created_count

    except Exchange.DoesNotExist:
        logger.error(f"Exchange with code {exchange_code} does not exist for fetch candles task.")
        raise
    except DataFetchError as e:
        logger.error(f"DataFetchError in fetch candles task for {symbol} on {exchange_code} ({interval}): {str(e)}")
        raise # یا مدیریت خطا و تلاش مجدد
    except Exception as e:
        logger.error(f"Unexpected error in fetch candles task for {symbol} on {exchange_code} ({interval}): {str(e)}")
        raise

@shared_task
def place_order_task(account_id: int, bot_id: int, order_params: dict) -> dict:
    """
    Celery task for placing an order on the exchange asynchronously.
    """
    try:
        from apps.bots.models import TradingBot # ایمپورت درون تابع برای جلوگیری از حلقه
        account = ExchangeAccount.objects.get(id=account_id)
        bot = TradingBot.objects.get(id=bot_id)

        service = ExchangeService()
        order_response = service.place_order(account, bot, order_params)
        logger.info(f"Order placed successfully via task for bot {bot.name} on account {account.label}.")
        return order_response
    except (ExchangeAccount.DoesNotExist, TradingBot.DoesNotExist) as e:
        logger.error(f"Object does not exist for place order task: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in place order task: {str(e)}")
        raise

# سایر تاسک‌های مرتبط می‌توانند در این فایل اضافه شوند
# مثلاً تاسک برای لغو سفارش، به‌روزرسانی موجودی، یا ارسال هشدار
