# apps/exchanges/signals.py

from django.db.models.signals import post_save, pre_delete, m2m_changed
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
import logging
from .models import (
    ExchangeAccount,
    Wallet,
    WalletBalance,
    OrderHistory,
    MarketDataCandle,
    AggregatedPortfolio,
    AggregatedAssetPosition,
    # سایر مدل‌های exchanges
)
from apps.core.models import AuditLog # استفاده از مدل AuditLog از core
from apps.core.tasks import log_audit_event_task # استفاده از تاسک AuditLog از core
from apps.core.services import AuditService # استفاده از سرویس AuditLog از core
from apps.core.helpers import validate_ip_list, get_client_ip # استفاده از توابع کمکی از core
from apps.core.exceptions import SecurityException # استفاده از استثناهای core
from .tasks import (
    sync_exchange_account_task, # تاسک خاص exchanges
    # ... سایر تاسک‌های exchanges ...
)
from apps.accounts.models import CustomUser # import مدل کاربر
from apps.bots.models import TradingBot # import مدل بات

logger = logging.getLogger(__name__)

# --- سیگنال‌های ExchangeAccount ---

@receiver(post_save, sender=ExchangeAccount)
def handle_exchange_account_save(sender, instance, created, **kwargs):
    """
    Signal handler for ExchangeAccount model save events.
    Performs actions like:
    - Creating a default Spot wallet upon account creation.
    - Logging the event to the audit trail (using core's AuditLog or AuditService).
    - Triggering an initial sync task (optional).
    """
    if created:
        # 1. ایجاد یک کیف پول SPOT پیش‌فرض
        Wallet.objects.get_or_create(
            exchange_account=instance,
            wallet_type='SPOT',
            is_default=True,
            defaults={'description': f'Default Spot wallet for {instance.exchange.name}'}
        )
        logger.info(f"Default Spot wallet created for new ExchangeAccount {instance.label}.")

        # 2. فعال‌سازی تاسک همگام‌سازی اولیه (اختیاری)
        # sync_exchange_account_task.delay(instance.id)

    # 3. ثبت واقعه در سیستم حسابرسی (Audit Trail) - از core استفاده می‌کنیم
    action = 'EXCHANGE_ACCOUNT_CREATED' if created else 'EXCHANGE_ACCOUNT_UPDATED'
    AuditService.log_action(
        user=instance.owner, # تغییر: owner به جای user
        action=action,
        target_model_name='ExchangeAccount',
        target_id=instance.id,
        details={
            'account_label': instance.label,
            'exchange_name': instance.exchange.name,
            'is_active': instance.is_active,
            'is_paper_trading': instance.is_paper_trading,
            'changed_fields': list(kwargs.get('update_fields', [])) # فقط فیلدهای بروزرسانی شده
        },
        request=None # در سیگنال، request وجود ندارد
    )
    # یا اگر بخواهید مستقیماً تاسک را فراخوانی کنید:
    # log_audit_event_task.delay(
    #     user_id=instance.owner.id, # تغییر: owner به جای user
    #     action=action,
    #     target_model_name='ExchangeAccount',
    #     target_id=instance.id,
    #     details={'account_label': instance.label, 'exchange_name': instance.exchange.name},
    #     ip_address=None, # در سیگنال، IP قابل دسترسی نیست
    #     user_agent=None
    # )

    logger.info(f"ExchangeAccount {instance.label} (ID: {instance.id}) saved. Action logged.")


@receiver(pre_delete, sender=ExchangeAccount)
def handle_exchange_account_delete(sender, instance, **kwargs):
    """
    Signal handler for ExchangeAccount model delete events.
    Performs actions like:
    - Logging the deletion event.
    - Triggering a cleanup task (e.g., invalidate cache entries, notify agents).
    - Potentially revoking API access on the exchange side (if applicable and safe).
    """
    # ثبت واقعه حذف در سیستم حسابرسی
    AuditService.log_action(
        user=instance.owner, # تغییر: owner به جای user
        action='EXCHANGE_ACCOUNT_DELETED',
        target_model_name='ExchangeAccount',
        target_id=instance.id,
        details={'account_label': instance.label, 'exchange_name': instance.exchange.name},
        request=None
    )

    # فعال‌سازی تاسک برای پاکسازی داده‌های مرتبط در کش یا سایر سیستم‌ها
    # from apps.core.tasks import invalidate_cache_for_instrument_task # از core
    # invalidate_cache_for_instrument_task.delay(instance.id)

    # فعال‌سازی تاسک برای اطلاع‌رسانی به عامل‌های مرتبط (اگر وجود داشت)
    # from apps.agents.tasks import notify_agents_of_account_removal_task
    # notify_agents_of_account_removal_task.delay(instance.id)

    logger.info(f"ExchangeAccount {instance.label} (ID: {instance.id}) for user {instance.owner.email} is being deleted.")


# --- سیگنال‌های Wallet ---

@receiver(post_save, sender=Wallet)
def handle_wallet_save(sender, instance, created, **kwargs):
    """
    Signal handler for Wallet model save events.
    Logs creation/update.
    """
    action = 'WALLET_CREATED' if created else 'WALLET_UPDATED'
    AuditService.log_action(
        user=instance.exchange_account.owner, # مالک حساب صرافی
        action=action,
        target_model_name='Wallet',
        target_id=instance.id,
        details={
            'wallet_type': instance.wallet_type,
            'account_label': instance.exchange_account.label,
            'exchange_name': instance.exchange_account.exchange.name,
            'is_default': instance.is_default,
        },
        request=None
    )
    logger.info(f"Wallet {instance.wallet_type} (ID: {instance.id}) for account {instance.exchange_account.label} saved. Action logged.")


@receiver(pre_delete, sender=Wallet)
def handle_wallet_delete(sender, instance, **kwargs):
    """
    Signal handler for Wallet model delete events.
    Logs the deletion.
    """
    AuditService.log_action(
        user=instance.exchange_account.owner,
        action='WALLET_DELETED',
        target_model_name='Wallet',
        target_id=instance.id,
        details={'wallet_type': instance.wallet_type, 'account_label': instance.exchange_account.label},
        request=None
    )
    logger.info(f"Wallet {instance.wallet_type} (ID: {instance.id}) for account {instance.exchange_account.label} deleted. Action logged.")


# --- سیگنال‌های WalletBalance ---

@receiver(post_save, sender=WalletBalance)
def handle_wallet_balance_save(sender, instance, created, **kwargs):
    """
    Signal handler for WalletBalance model save events.
    Logs balance changes. Can trigger alerts if balance drops below threshold.
    """
    action = 'BALANCE_UPDATED'
    AuditService.log_action(
        user=instance.wallet.exchange_account.owner, # مالک حساب صرافی
        action=action,
        target_model_name='WalletBalance',
        target_id=instance.id,
        details={
            'asset_symbol': instance.asset_symbol,
            'total_balance': str(instance.total_balance),
            'available_balance': str(instance.available_balance),
            'wallet_type': instance.wallet.wallet_type,
            'account_label': instance.wallet.exchange_account.label,
            'exchange_name': instance.wallet.exchange_account.exchange.name,
        },
        request=None
    )
    logger.info(f"Balance for {instance.asset_symbol} in wallet {instance.wallet} (ID: {instance.id}) updated. Action logged.")

    # مثال: چک کردن موجودی و ارسال هشدار
    # if instance.available_balance < Decimal('0.001'): # یا مقدار مشخصی
    #     from apps.core.tasks import send_low_balance_alert_task # از core
    #     send_low_balance_alert_task.delay(instance.wallet.exchange_account.id, instance.asset_symbol, instance.available_balance)


# --- سیگنال‌های OrderHistory ---

@receiver(post_save, sender=OrderHistory)
def handle_order_history_save(sender, instance, created, **kwargs):
    """
    Signal handler for OrderHistory model save events.
    Logs order events. Can trigger portfolio updates, risk checks, or strategy reactions.
    """
    action = 'ORDER_CREATED' if created else 'ORDER_UPDATED'
    AuditService.log_action(
        user=instance.exchange_account.owner, # مالک حساب سفارش
        action=action,
        target_model_name='OrderHistory',
        target_id=instance.id,
        details={
            'order_id': instance.order_id,
            'symbol': instance.symbol,
            'side': instance.side,
            'status': instance.status,
            'price': str(instance.price),
            'quantity': str(instance.quantity),
            'executed_quantity': str(instance.executed_quantity),
            'account_label': instance.exchange_account.label,
            'exchange_name': instance.exchange_account.exchange.name,
            'bot_name': getattr(instance.trading_bot, 'name', None) # فقط اگر bot وجود داشت
        },
        request=None
    )

    if created:
        logger.info(f"New order history record created: {instance.order_id} for {instance.symbol} on {instance.exchange_account.label}.")
    else:
        logger.info(f"Order history record updated: {instance.order_id} (Status: {instance.status}).")

    # مثال: چک کردن تغییر وضعیت و انجام عملیات متناسب (مثلاً اگر FILLED شد)
    if instance.status == 'FILLED':
        AuditService.log_action(
            user=instance.exchange_account.owner,
            action='ORDER_FILLED',
            target_model_name='OrderHistory',
            target_id=instance.id,
            details={'order_id': instance.order_id, 'symbol': instance.symbol, 'fill_price': str(instance.price), 'fill_quantity': str(instance.executed_quantity)},
            request=None
        )
        # فعال‌سازی تاسک یا سرویس برای بروزرسانی پرتفوی یا موقعیت
        # from .services import PortfolioService
        # PortfolioService.update_position_after_fill(instance)


# --- سیگنال‌های MarketDataCandle ---

@receiver(post_save, sender=MarketDataCandle)
def handle_market_data_candle_save(sender, instance, created, **kwargs):
    """
    Signal handler for MarketDataCandle model save events.
    Logs data ingestion. Can trigger strategy analysis or cache updates.
    """
    if created:
        logger.info(f"New market data candle saved: {instance.symbol} ({instance.interval}) at {instance.open_time} on {instance.exchange.name}.")
        # ثبت واقعه در حسابرسی
        AuditService.log_action(
            user=None, # منبع داده، نه کاربر
            action='CANDLE_ADDED',
            target_model_name='MarketDataCandle',
            target_id=instance.id,
            details={
                'symbol': instance.symbol,
                'interval': instance.interval,
                'exchange_name': instance.exchange.name,
                'open_time': instance.open_time.isoformat(),
                'close_price': str(instance.close),
            },
            request=None
        )

        # مثال: فعال‌سازی تاسک تحلیل استراتژی (در صورت نیاز)
        # from apps.strategies.tasks import analyze_candle_task
        # analyze_candle_task.delay(instance.id)

    # در صورت بروزرسانی یک کندل موجود (مثلاً اصلاح داده)
    else:
        logger.info(f"Market data candle updated: {instance.symbol} ({instance.interval}) at {instance.open_time}.")
        AuditService.log_action(
            user=None,
            action='CANDLE_MODIFIED',
            target_model_name='MarketDataCandle',
            target_id=instance.id,
            details={'symbol': instance.symbol, 'interval': instance.interval, 'open_time': instance.open_time.isoformat()},
            request=None
        )

        # مثال: فعال‌سازی تاسک بروزرسانی کش
        # from apps.core.tasks import update_cache_for_candle_task # از core
        # update_cache_for_candle_task.delay(instance.id)


# --- سیگنال‌های AggregatedPortfolio ---

@receiver(post_save, sender=AggregatedPortfolio)
def handle_aggregated_portfolio_save(sender, instance, created, **kwargs):
    """
    Signal handler for AggregatedPortfolio model save events.
    Logs portfolio changes.
    """
    action = 'PORTFOLIO_CREATED' if created else 'PORTFOLIO_UPDATED'
    AuditService.log_action(
        user=instance.owner, # تغییر: owner به جای user
        action=action,
        target_model_name='AggregatedPortfolio',
        target_id=instance.id,
        details={
            'base_currency': instance.base_currency,
            'total_equity': str(instance.total_equity),
            'total_unrealized_pnl': str(instance.total_unrealized_pnl),
            'total_realized_pnl': str(instance.total_realized_pnl),
        },
        request=None
    )
    logger.info(f"Aggregated portfolio (ID: {instance.id}) for user {instance.owner.email} saved. Action logged.")


# --- سیگنال‌های AggregatedAssetPosition ---

@receiver(post_save, sender=AggregatedAssetPosition)
def handle_aggregated_asset_position_save(sender, instance, created, **kwargs):
    """
    Signal handler for AggregatedAssetPosition model save events.
    Logs asset position changes.
    """
    action = 'ASSET_POSITION_CREATED' if created else 'ASSET_POSITION_UPDATED'
    AuditService.log_action(
        user=instance.aggregated_portfolio.owner, # مالک پرتفوی تجمیعی
        action=action,
        target_model_name='AggregatedAssetPosition',
        target_id=instance.id,
        details={
            'asset_symbol': instance.asset_symbol,
            'total_quantity': str(instance.total_quantity),
            'total_value_in_base_currency': str(instance.total_value_in_base_currency),
            'portfolio_id': str(instance.aggregated_portfolio.id),
        },
        request=None
    )
    logger.info(f"Aggregated asset position for {instance.asset_symbol} (ID: {instance.id}) updated. Action logged.")


# --- سیگنال‌های مرتبط با M2M ---
# مثال: زمانی که یک بات به یک حساب صرافی متصل یا قطع می‌شود

@receiver(m2m_changed, sender=ExchangeAccount.linked_bots.through)
def handle_exchange_account_bots_change(sender, instance, action, reverse, model, pk_set, **kwargs):
    """
    Signal handler for changes to the linked_bots M2M relation on ExchangeAccount.
    Logs the connection/disconnection.
    """
    if action in ["post_add", "post_remove", "post_clear"]:
        bot_names = model.objects.filter(pk__in=pk_set).values_list('name', flat=True) if pk_set else []
        user_email = instance.owner.email # تغییر: owner به جای user

        if action == "post_add":
            logger.info(f"Bots {list(bot_names)} linked to ExchangeAccount {instance.label} for user {user_email}.")
            AuditService.log_action(
                user=instance.owner,
                action='BOTS_LINKED_TO_ACCOUNT',
                target_model_name='ExchangeAccount',
                target_id=instance.id,
                details={'bot_names': list(bot_names)},
                request=None
            )
        elif action == "post_remove":
            logger.info(f"Bots {list(bot_names)} unlinked from ExchangeAccount {instance.label} for user {user_email}.")
            AuditService.log_action(
                user=instance.owner,
                action='BOTS_UNLINKED_FROM_ACCOUNT',
                target_model_name='ExchangeAccount',
                target_id=instance.id,
                details={'bot_names': list(bot_names)},
                request=None
            )
        elif action == "post_clear":
            logger.info(f"All bots unlinked from ExchangeAccount {instance.label} for user {user_email}.")
            AuditService.log_action(
                user=instance.owner,
                action='ALL_BOTS_UNLINKED_FROM_ACCOUNT',
                target_model_name='ExchangeAccount',
                target_id=instance.id,
                details={},
                request=None
            )


logger.info("Exchanges signals loaded successfully.")
