# apps/exchanges/signals.py

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
import logging
from .models import ExchangeAccount, OrderHistory, MarketDataCandle
from .tasks import sync_exchange_account_task # فرض بر این است که این تاسک وجود دارد
from apps.core.models import AuditLog # فرض بر این است که یک مدل کلی برای لاگ وجود دارد

logger = logging.getLogger(__name__)

@receiver(post_save, sender=ExchangeAccount)
def handle_exchange_account_save(sender, instance, created, **kwargs):
    """
    Signal handler for ExchangeAccount model save events.
    Can be used for actions like:
    - Creating a default Spot wallet upon account creation.
    - Triggering an initial sync task.
    - Logging the creation/update.
    """
    if created:
        # مثال: ایجاد یک کیف پول Spot پیش‌فرض
        from .models import Wallet
        Wallet.objects.get_or_create(
            exchange_account=instance,
            wallet_type='SPOT',
            is_default=True,
            defaults={'description': f'Default Spot wallet for {instance.exchange.name}'}
        )
        logger.info(f"Default Spot wallet created for new ExchangeAccount {instance.label}.")

        # مثال: فعال‌سازی تاسک همگام‌سازی اولیه (اختیاری)
        # sync_exchange_account_task.delay(instance.id)

    # مثال: ثبت واقعه در سیستم Audit Log
    action = 'CREATED' if created else 'UPDATED'
    AuditLog.objects.create(
        user=instance.user,
        action=action,
        target_model='ExchangeAccount',
        target_id=instance.id,
        details=f"Account {instance.label} on {instance.exchange.name} was {action.lower()}."
    )

@receiver(post_save, sender=OrderHistory)
def handle_order_history_save(sender, instance, created, **kwargs):
    """
    Signal handler for OrderHistory model save events.
    Can be used for actions like:
    - Updating the aggregated portfolio upon order fill.
    - Triggering risk management checks.
    - Logging the order event.
    """
    if created:
        logger.info(f"New order history record created: {instance.order_id} for {instance.symbol} on {instance.exchange_account.label}.")
        # مثال: فراخوانی تابع به‌روزرسانی پرتفوی (در یک سرویس جداگانه)
        # from .services import PortfolioService
        # PortfolioService.update_portfolio_for_order(instance)
    else:
        logger.info(f"Order history record updated: {instance.order_id} (Status: {instance.status}).")
        # مثال: چک کردن تغییر وضعیت و انجام عملیات متناسب (مثلاً اگر FILLED شد)
        if instance.status == 'FILLED':
             # from .services import PortfolioService
             # PortfolioService.update_position_after_fill(instance)
             pass # منطق مربوطه در سرویس

@receiver(post_save, sender=MarketDataCandle)
def handle_market_data_candle_save(sender, instance, created, **kwargs):
    """
    Signal handler for MarketDataCandle model save events.
    Can be used for actions like:
    - Triggering strategy analysis if a new candle is added.
    - Updating cached data for faster queries.
    - Logging the data ingestion.
    """
    if created:
        logger.info(f"New market data candle saved: {instance.symbol} ({instance.interval}) at {instance.open_time} on {instance.exchange.name}.")
        # مثال: فعال‌سازی تاسک تحلیل استراتژی (در صورت نیاز)
        # from apps.strategies.tasks import analyze_candle_task
        # analyze_candle_task.delay(instance.id)
    # در صورت بروزرسانی یک کندل موجود (مثلاً اصلاح داده)
    else:
        logger.info(f"Market data candle updated: {instance.symbol} ({instance.interval}) at {instance.open_time}.")

@receiver(pre_delete, sender=ExchangeAccount)
def handle_exchange_account_delete(sender, instance, **kwargs):
    """
    Signal handler for ExchangeAccount model delete events.
    Can be used for actions like:
    - Logging the deletion.
    - Cleaning up related data if necessary (with caution!).
    - Revoking API access on the exchange side (if applicable and safe).
    """
    logger.info(f"ExchangeAccount {instance.label} for user {instance.user.email} is being deleted.")
    # مثال: ثبت واقعه در سیستم Audit Log
    AuditLog.objects.create(
        user=instance.user,
        action='DELETED',
        target_model='ExchangeAccount',
        target_id=instance.id,
        details=f"Account {instance.label} on {instance.exchange.name} was deleted."
    )
    # توجه: حذف کامل داده‌های مرتبط مانند Wallets, Balances, Orders باید با دقت انجام شود
    # و معمولاً ترجیح می‌رود داده‌ها منقل شوند تا کاملاً حذف شوند (Soft Delete یا تغییر وضعیت).

# سایر سیگنال‌های مرتبط می‌توانند در این فایل اضافه شوند
