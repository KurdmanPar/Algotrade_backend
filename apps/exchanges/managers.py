# apps/exchanges/managers.py

from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()

class ExchangeAccountManager(models.Manager):
    """
    Custom manager for ExchangeAccount model with additional query methods.
    """

    def active(self):
        """
        Returns active exchange accounts.
        """
        return self.filter(is_active=True)

    def for_user(self, user):
        """
        Returns exchange accounts belonging to a specific user.
        """
        return self.filter(user=user)

    def with_api_access(self):
        """
        Returns exchange accounts that have valid API keys stored.
        This assumes the encrypted fields are not empty strings.
        """
        return self.filter(
            _api_key_encrypted__isnull=False,
            _api_key_encrypted__gt='', # Greater than empty string
            _api_secret_encrypted__isnull=False,
            _api_secret_encrypted__gt=''
        )

    def for_exchange(self, exchange_code):
        """
        Returns exchange accounts linked to a specific exchange (by code).
        """
        return self.filter(exchange__code__iexact=exchange_code)

    def with_linked_bot(self, bot_id):
        """
        Returns exchange accounts that have a specific bot linked to them.
        """
        return self.filter(linked_bots__id=bot_id)

    def paper_trading_accounts(self):
        """
        Returns exchange accounts configured for paper trading.
        """
        return self.filter(is_paper_trading=True)

    def synced_after(self, datetime_obj):
        """
        Returns exchange accounts synced after a specific datetime.
        """
        return self.filter(last_sync_at__gt=datetime_obj)

    def get_by_label_for_user(self, label, user):
        """
        Retrieves an exchange account by its label and user.
        """
        try:
            return self.get(label=label, user=user)
        except self.model.DoesNotExist:
            return None

class WalletManager(models.Manager):
    """
    Custom manager for Wallet model with additional query methods.
    """

    def for_account(self, exchange_account):
        """
        Returns wallets associated with a specific exchange account.
        """
        return self.filter(exchange_account=exchange_account)

    def of_type(self, wallet_type):
        """
        Returns wallets of a specific type (e.g., SPOT, FUTURES).
        """
        return self.filter(wallet_type__iexact=wallet_type)

    def default_for_account(self, exchange_account):
        """
        Returns the default wallet for a specific exchange account.
        """
        return self.filter(exchange_account=exchange_account, is_default=True).first()

class WalletBalanceManager(models.Manager):
    """
    Custom manager for WalletBalance model with additional query methods.
    """

    def for_wallet(self, wallet):
        """
        Returns balances associated with a specific wallet.
        """
        return self.filter(wallet=wallet)

    def for_asset(self, asset_symbol):
        """
        Returns balances for a specific asset symbol across all wallets.
        """
        return self.filter(asset_symbol__iexact=asset_symbol)

    def with_available_balance_gt(self, amount: Decimal):
        """
        Returns balances with available balance greater than a specified amount.
        """
        return self.filter(available_balance__gt=amount)

    def total_for_wallet(self, wallet):
        """
        Calculates the total available balance across all assets in a specific wallet.
        """
        balances = self.for_wallet(wallet)
        total = balances.aggregate(total=models.Sum('available_balance'))['total']
        return total or Decimal('0')

class OrderHistoryManager(models.Manager):
    """
    Custom manager for OrderHistory model with additional query methods.
    """

    def for_account(self, exchange_account):
        """
        Returns order history for a specific exchange account.
        """
        return self.filter(exchange_account=exchange_account)

    def for_bot(self, bot):
        """
        Returns order history executed by a specific bot.
        """
        return self.filter(trading_bot=bot)

    def of_status(self, status):
        """
        Returns orders with a specific status (e.g., FILLED, CANCELED).
        """
        return self.filter(status__iexact=status)

    def of_side(self, side):
        """
        Returns orders with a specific side (BUY, SELL).
        """
        return self.filter(side__iexact=side)

    def placed_after(self, datetime_obj):
        """
        Returns orders placed after a specific datetime.
        """
        return self.filter(time_placed__gt=datetime_obj)

    def placed_before(self, datetime_obj):
        """
        Returns orders placed before a specific datetime.
        """
        return self.filter(time_placed__lt=datetime_obj)

    def for_symbol(self, symbol):
        """
        Returns orders for a specific trading symbol.
        """
        return self.filter(symbol__iexact=symbol)

class MarketDataCandleManager(models.Manager):
    """
    Custom manager for MarketDataCandle model with additional query methods.
    """

    def for_symbol(self, symbol):
        """
        Returns candles for a specific symbol.
        """
        return self.filter(symbol__iexact=symbol)

    def for_exchange(self, exchange_code):
        """
        Returns candles for a specific exchange (by code).
        """
        return self.filter(exchange__code__iexact=exchange_code)

    def of_interval(self, interval):
        """
        Returns candles of a specific interval (e.g., 1h, 1d).
        """
        return self.filter(interval__iexact=interval)

    def in_date_range(self, start_date, end_date):
        """
        Returns candles within a specific date range (based on open_time).
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

# سایر منیجرهای مرتبط می‌توانند در این فایل اضافه شوند
