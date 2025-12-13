# apps/exchanges/managers.py

from django.db import models
from django.utils import timezone
from decimal import Decimal
import logging
from apps.core.models import BaseModel, BaseOwnedModel # import از core
from apps.core.managers import CoreBaseManager, CoreOwnedModelManager # اگر وجود داشتند
from apps.core.helpers import validate_ip_list # import از core
from apps.core.exceptions import CoreSystemException # import از core

logger = logging.getLogger(__name__)

# --- QuerySets سفارشی ---

class ExchangeAccountQuerySet(models.QuerySet):
    """
    Custom QuerySet for the ExchangeAccount model with specific filtering methods.
    """
    def active(self):
        """
        Filters for active exchange accounts.
        """
        return self.filter(is_active=True)

    def for_user(self, user):
        """
        Filters exchange accounts owned by a specific user.
        """
        return self.filter(owner=user) # تغییر: owner به جای user

    def for_exchange(self, exchange_code_or_id):
        """
        Filters exchange accounts linked to a specific exchange (by code or ID).
        """
        if isinstance(exchange_code_or_id, str):
            return self.filter(exchange__code__iexact=exchange_code_or_id)
        else:
            return self.filter(exchange_id=exchange_code_or_id)

    def paper_trading(self):
        """
        Filters paper trading accounts.
        """
        return self.filter(is_paper_trading=True)

    def real_trading(self):
        """
        Filters real trading accounts.
        """
        return self.filter(is_paper_trading=False)

    def with_api_access(self):
        """
        Filters exchange accounts that have stored API keys (assuming encrypted fields are not empty).
        """
        return self.filter(
            _api_key_encrypted__isnull=False,
            _api_key_encrypted__gt='',
            _api_secret_encrypted__isnull=False,
            _api_secret_encrypted__gt=''
        )

    def synced_after(self, datetime_obj):
        """
        Filters exchange accounts that were synced after a specific datetime.
        """
        return self.filter(last_sync_at__gt=datetime_obj)

    def requiring_sync(self, minutes_since_last_sync: int = 60):
        """
        Filters exchange accounts that haven't been synced for N minutes (or longer).
        Useful for scheduling periodic sync tasks.
        """
        cutoff_time = timezone.now() - timezone.timedelta(minutes=minutes_since_last_sync)
        return self.filter(
            models.Q(last_sync_at__isnull=True) | # حساب‌هایی که هیچ همگام‌سازی نداشته‌اند
            models.Q(last_sync_at__lt=cutoff_time) # یا زمان آخرین همگام‌سازی بیش از N دقیقه پیش بوده است
        )


class WalletQuerySet(models.QuerySet):
    """
    Custom QuerySet for the Wallet model.
    """
    def for_account(self, exchange_account):
        """
        Filters wallets associated with a specific exchange account.
        """
        return self.filter(exchange_account=exchange_account)

    def of_type(self, wallet_type):
        """
        Filters wallets of a specific type (e.g., SPOT, FUTURES).
        """
        return self.filter(wallet_type__iexact=wallet_type)

    def default_for_account(self, exchange_account):
        """
        Returns the default wallet for a specific exchange account.
        """
        return self.filter(exchange_account=exchange_account, is_default=True).first()

    def with_margin_enabled(self):
        """
        Filters wallets where margin trading is enabled.
        """
        return self.filter(is_margin_enabled=True)

    def total_balance_for_account(self, exchange_account):
        """
        Calculates the total available balance across all wallets for an account.
        """
        wallets = self.for_account(exchange_account)
        total = wallets.aggregate(total=models.Sum('balances__available_balance'))['total']
        return total or Decimal('0')


class WalletBalanceQuerySet(models.QuerySet):
    """
    Custom QuerySet for the WalletBalance model.
    """
    def for_wallet(self, wallet):
        """
        Filters balances associated with a specific wallet.
        """
        return self.filter(wallet=wallet)

    def for_asset(self, asset_symbol):
        """
        Filters balances for a specific asset symbol across all wallets.
        """
        return self.filter(asset_symbol__iexact=asset_symbol)

    def with_available_balance_gt(self, amount: Decimal):
        """
        Filters balances with available balance greater than a specified amount.
        """
        return self.filter(available_balance__gt=amount)

    def total_for_wallet(self, wallet):
        """
        Calculates the total available balance across all assets in a specific wallet.
        """
        balances = self.for_wallet(wallet)
        total = balances.aggregate(total=models.Sum('available_balance'))['total']
        return total or Decimal('0')


class OrderHistoryQuerySet(models.QuerySet):
    """
    Custom QuerySet for the OrderHistory model.
    """
    def for_account(self, exchange_account):
        """
        Filters order history for a specific exchange account.
        """
        return self.filter(exchange_account=exchange_account)

    def for_bot(self, bot):
        """
        Filters order history executed by a specific bot.
        """
        return self.filter(trading_bot=bot)

    def of_status(self, status):
        """
        Filters orders with a specific status (e.g., FILLED, CANCELED).
        """
        return self.filter(status__iexact=status)

    def of_side(self, side):
        """
        Filters orders with a specific side (BUY, SELL).
        """
        return self.filter(side__iexact=side)

    def placed_after(self, datetime_obj):
        """
        Filters orders placed after a specific datetime.
        """
        return self.filter(time_placed__gt=datetime_obj)

    def placed_before(self, datetime_obj):
        """
        Filters orders placed before a specific datetime.
        """
        return self.filter(time_placed__lt=datetime_obj)

    def for_symbol(self, symbol):
        """
        Filters orders for a specific trading symbol.
        """
        return self.filter(symbol__iexact=symbol)

    def with_commission_gt(self, amount: Decimal):
        """
        Filters orders with commission paid greater than a specified amount.
        """
        return self.filter(commission__gt=amount)

    def in_date_range(self, start_date, end_date):
        """
        Filters orders placed within a specific date range.
        """
        return self.filter(time_placed__date__gte=start_date.date(), time_placed__date__lte=end_date.date())


class MarketDataCandleQuerySet(models.QuerySet):
    """
    Custom QuerySet for the MarketDataCandle model.
    """
    def for_symbol(self, symbol):
        """
        Filters candles for a specific symbol.
        """
        return self.filter(symbol__iexact=symbol)

    def for_exchange(self, exchange_code_or_id):
        """
        Filters candles for a specific exchange (by code or ID).
        """
        if isinstance(exchange_code_or_id, str):
            return self.filter(exchange__code__iexact=exchange_code_or_id)
        else:
            return self.filter(exchange_id=exchange_code_or_id)

    def of_interval(self, interval):
        """
        Filters candles of a specific interval (e.g., 1h, 1d).
        """
        return self.filter(interval__iexact=interval)

    def in_date_range(self, start_date, end_date):
        """
        Filters candles within a specific date range (based on open_time).
        """
        return self.filter(open_time__date__gte=start_date.date(), open_time__date__lte=end_date.date())

    def latest_for_symbol(self, symbol, interval='1d'):
        """
        Returns the latest candle for a given symbol and interval.
        """
        return self.filter(
            symbol__iexact=symbol,
            interval__iexact=interval
        ).order_by('-open_time').first()

    def ordered_by_time(self, ascending=False):
        """
        Returns candles ordered by open_time.
        """
        order = 'open_time' if ascending else '-open_time'
        return self.order_by(order)


class AggregatedPortfolioQuerySet(models.QuerySet):
    """
    Custom QuerySet for the AggregatedPortfolio model.
    """
    def for_user(self, user):
        """
        Filters aggregated portfolios owned by a specific user.
        """
        return self.filter(owner=user) # تغییر: owner به جای user

    def by_base_currency(self, currency_code):
        """
        Filters portfolios with a specific base currency.
        """
        return self.filter(base_currency__iexact=currency_code)


class AggregatedAssetPositionQuerySet(models.QuerySet):
    """
    Custom QuerySet for the AggregatedAssetPosition model.
    """
    def for_portfolio(self, portfolio):
        """
        Filters positions associated with a specific aggregated portfolio.
        """
        return self.filter(aggregated_portfolio=portfolio)

    def for_asset(self, asset_symbol):
        """
        Filters positions for a specific asset symbol.
        """
        return self.filter(asset_symbol__iexact=asset_symbol)

    def total_quantity_for_asset(self, asset_symbol):
        """
        Calculates the total quantity held for a specific asset across all portfolios.
        """
        positions = self.for_asset(asset_symbol)
        total = positions.aggregate(total=models.Sum('total_quantity'))['total']
        return total or Decimal('0')

    def total_value_for_portfolio(self, portfolio):
        """
        Calculates the total value of all positions in a specific portfolio.
        """
        positions = self.for_portfolio(portfolio)
        total = positions.aggregate(total=models.Sum('total_value_in_base_currency'))['total']
        return total or Decimal('0')


# --- منیجرهای سفارشی ---

class ExchangeAccountManager(models.Manager):
    """
    Custom Manager for the ExchangeAccount model.
    Uses the custom ExchangeAccountQuerySet.
    """
    def get_queryset(self):
        return ExchangeAccountQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()

    def for_user(self, user):
        return self.get_queryset().for_user(user)

    def for_exchange(self, exchange_code_or_id):
        return self.get_queryset().for_exchange(exchange_code_or_id)

    def paper_trading(self):
        return self.get_queryset().paper_trading()

    def real_trading(self):
        return self.get_queryset().real_trading()

    def with_api_access(self):
        return self.get_queryset().with_api_access()

    def synced_after(self, datetime_obj):
        return self.get_queryset().synced_after(datetime_obj)

    def requiring_sync(self, minutes_since_last_sync: int = 60):
        return self.get_queryset().requiring_sync(minutes_since_last_sync)


class WalletManager(models.Manager):
    """
    Custom Manager for the Wallet model.
    Uses the custom WalletQuerySet.
    """
    def get_queryset(self):
        return WalletQuerySet(self.model, using=self._db)

    def for_account(self, exchange_account):
        return self.get_queryset().for_account(exchange_account)

    def of_type(self, wallet_type):
        return self.get_queryset().of_type(wallet_type)

    def default_for_account(self, exchange_account):
        return self.get_queryset().default_for_account(exchange_account)

    def with_margin_enabled(self):
        return self.get_queryset().with_margin_enabled()

    def total_balance_for_account(self, exchange_account):
        return self.get_queryset().total_balance_for_account(exchange_account)


class WalletBalanceManager(models.Manager):
    """
    Custom Manager for the WalletBalance model.
    Uses the custom WalletBalanceQuerySet.
    """
    def get_queryset(self):
        return WalletBalanceQuerySet(self.model, using=self._db)

    def for_wallet(self, wallet):
        return self.get_queryset().for_wallet(wallet)

    def for_asset(self, asset_symbol):
        return self.get_queryset().for_asset(asset_symbol)

    def with_available_balance_gt(self, amount: Decimal):
        return self.get_queryset().with_available_balance_gt(amount)

    def total_for_wallet(self, wallet):
        return self.get_queryset().total_for_wallet(wallet)


class OrderHistoryManager(models.Manager):
    """
    Custom Manager for the OrderHistory model.
    Uses the custom OrderHistoryQuerySet.
    """
    def get_queryset(self):
        return OrderHistoryQuerySet(self.model, using=self._db)

    def for_account(self, exchange_account):
        return self.get_queryset().for_account(exchange_account)

    def for_bot(self, bot):
        return self.get_queryset().for_bot(bot)

    def of_status(self, status):
        return self.get_queryset().of_status(status)

    def of_side(self, side):
        return self.get_queryset().of_side(side)

    def placed_after(self, datetime_obj):
        return self.get_queryset().placed_after(datetime_obj)

    def placed_before(self, datetime_obj):
        return self.get_queryset().placed_before(datetime_obj)

    def for_symbol(self, symbol):
        return self.get_queryset().for_symbol(symbol)

    def with_commission_gt(self, amount: Decimal):
        return self.get_queryset().with_commission_gt(amount)

    def in_date_range(self, start_date, end_date):
        return self.get_queryset().in_date_range(start_date, end_date)


class MarketDataCandleManager(models.Manager):
    """
    Custom Manager for the MarketDataCandle model.
    Uses the custom MarketDataCandleQuerySet.
    """
    def get_queryset(self):
        return MarketDataCandleQuerySet(self.model, using=self._db)

    def for_symbol(self, symbol):
        return self.get_queryset().for_symbol(symbol)

    def for_exchange(self, exchange_code_or_id):
        return self.get_queryset().for_exchange(exchange_code_or_id)

    def of_interval(self, interval):
        return self.get_queryset().of_interval(interval)

    def in_date_range(self, start_date, end_date):
        return self.get_queryset().in_date_range(start_date, end_date)

    def latest_for_symbol(self, symbol, interval='1d'):
        return self.get_queryset().latest_for_symbol(symbol, interval)

    def ordered_by_time(self, ascending=False):
        return self.get_queryset().ordered_by_time(ascending)


class AggregatedPortfolioManager(models.Manager):
    """
    Custom Manager for the AggregatedPortfolio model.
    Uses the custom AggregatedPortfolioQuerySet.
    """
    def get_queryset(self):
        return AggregatedPortfolioQuerySet(self.model, using=self._db)

    def for_user(self, user):
        return self.get_queryset().for_user(user)

    def by_base_currency(self, currency_code):
        return self.get_queryset().by_base_currency(currency_code)


class AggregatedAssetPositionManager(models.Manager):
    """
    Custom Manager for the AggregatedAssetPosition model.
    Uses the custom AggregatedAssetPositionQuerySet.
    """
    def get_queryset(self):
        return AggregatedAssetPositionQuerySet(self.model, using=self._db)

    def for_portfolio(self, portfolio):
        return self.get_queryset().for_portfolio(portfolio)

    def for_asset(self, asset_symbol):
        return self.get_queryset().for_asset(asset_symbol)

    def total_quantity_for_asset(self, asset_symbol):
        return self.get_queryset().total_quantity_for_asset(asset_symbol)

    def total_value_for_portfolio(self, portfolio):
        return self.get_queryset().total_value_for_portfolio(portfolio)


# --- منیجرهای مدل‌های دیگر (اگر نیاز باشد) ---
# می‌توانید برای سایر مدل‌هایی که در exchanges/models.py تعریف می‌کنید نیز QuerySet و Manager سفارشی بنویسید
# مثلاً اگر مدل InstrumentExchangeMap وجود داشت:
# class InstrumentExchangeMapQuerySet(models.QuerySet):
#     def active(self):
#         return self.filter(is_active=True)
#     def for_exchange(self, exchange):
#         return self.filter(exchange=exchange)
#     def for_instrument(self, instrument):
#         return self.filter(instrument=instrument)
#
# class InstrumentExchangeMapManager(models.Manager):
#     def get_queryset(self):
#         return InstrumentExchangeMapQuerySet(self.model, using=self._db)

logger.info("Exchanges managers loaded successfully.")
