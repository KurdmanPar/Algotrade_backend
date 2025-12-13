# apps/exchanges/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel, BaseOwnedModel # استفاده از مدل‌های پایه از core
from apps.core.encryption import encrypt_field, decrypt_field # استفاده از ابزار رمزنگاری از core
from apps.core.helpers import validate_ip_list # استفاده از تابع کمکی از core
from apps.core.exceptions import DataIntegrityException # استفاده از استثناهای core
from apps.accounts.models import CustomUser # import مدل کاربر از اپلیکیشن accounts
from apps.bots.models import TradingBot # import مدل بات از اپلیکیشن bots (اگر وجود داشته باشد)
from decimal import Decimal
import logging
import re

logger = logging.getLogger(__name__)

# --- مدل‌های اصلی صرافی و حساب ---

class Exchange(BaseModel): # استفاده از BaseModel از core
    """
    تعریف صرافی‌ها (مثلاً: Binance, Coinbase).
    """
    EXCHANGE_TYPE_CHOICES = [
        ("CRYPTO", _("Crypto Exchange")),
        ("STOCK", _("Stock Broker")),
        ("FOREX", _("Forex Broker")),
        ("FUTURES", _("Futures Exchange")),
        ("OPTIONS", _("Options Exchange")),
    ]
    name = models.CharField(max_length=128, verbose_name=_("Name"))
    code = models.CharField(max_length=32, unique=True, verbose_name=_("Code"))  # e.g. BINANCE
    type = models.CharField(max_length=16, choices=EXCHANGE_TYPE_CHOICES, verbose_name=_("Type"))
    base_url = models.URLField(verbose_name=_("Base API URL"))
    ws_url = models.URLField(blank=True, verbose_name=_("WebSocket URL"))
    api_docs_url = models.URLField(blank=True, verbose_name=_("API Documentation URL"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    is_sandbox = models.BooleanField(default=False, verbose_name=_("Is Sandbox/Testnet"))
    rate_limit_per_second = models.IntegerField(default=10, verbose_name=_("Rate Limit Per Second"))
    # اطلاعات مربوط به کارمزد و محدودیت‌ها
    fees_structure = models.JSONField(default=dict, blank=True, verbose_name=_("Fees Structure (JSON)"))
    limits = models.JSONField(default=dict, blank=True, verbose_name=_("Limits (JSON)"))

    class Meta:
        verbose_name = _("Exchange")
        verbose_name_plural = _("Exchanges")
        indexes = [
            models.Index(fields=['code']), # برای جستجوی سریع بر اساس کد
            models.Index(fields=['type', 'is_active']), # برای فیلتر کردن نوع و وضعیت
        ]

    def __str__(self):
        return self.name

    def clean(self):
        """
        Validates the model instance.
        """
        super().clean()
        # مثال: اعتبارسنجی فیلد fees_structure یا limits
        if self.fees_structure:
            # می‌توانید منطق خاصی برای اعتبارسنجی JSON اضافی اضافه کنید
            pass # یا استفاده از یک تابع کمکی یا validator
        if self.limits:
            # منطق اعتبارسنجی محدودیت‌ها
            pass


class ExchangeAccount(BaseOwnedModel): # استفاده از BaseOwnedModel از core برای مالکیت
    """
    اتصال حساب کاربر به یک صرافی خاص.
    """
    exchange = models.ForeignKey(
        "exchanges.Exchange", # استفاده از نام اپلیکیشن
        on_delete=models.CASCADE,
        related_name="accounts",
        verbose_name=_("Exchange")
    )
    label = models.CharField(max_length=128, blank=True, verbose_name=_("Account Label"))  # e.g. "My Main Binance Account"

    # امنیت: ذخیره رمزنگاری شده کلیدها
    _api_key_encrypted = models.TextField(verbose_name=_("Encrypted API Key"))
    _api_secret_encrypted = models.TextField(verbose_name=_("Encrypted API Secret"))
    # IV یا Nonce مورد نیاز برای رمزنگاری (اگر الگوریتم نیاز داشته باشد)
    encrypted_key_iv = models.CharField(max_length=255, blank=True, verbose_name=_("Encryption IV/Nonce"))
    extra_credentials = models.JSONField(default=dict, blank=True, verbose_name=_("Extra Credentials (JSON)"))

    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    is_paper_trading = models.BooleanField(default=False, verbose_name=_("Is Paper Trading Account"))
    last_sync_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Sync At"))
    # اطلاعات امنیتی
    last_login_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name=_("Last Login IP"))
    created_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name=_("Account Created IP"))
    # اطلاعات بروزرسانی شده
    account_info = models.JSONField(default=dict, blank=True, verbose_name=_("Account Info (JSON)")) # اطلاعات کامل حساب (مانند محدودیت‌ها، سطح کاربری و غیره)
    trading_permissions = models.JSONField(default=dict, blank=True, verbose_name=_("Trading Permissions (JSON)")) # مجوزهای معاملاتی
    # ارتباط با بات‌ها
    linked_bots = models.ManyToManyField(
        TradingBot,
        related_name="exchange_accounts_linked", # نام related_name باید منحصر به فرد باشد
        blank=True,
        verbose_name=_("Linked Bots")
    )

    class Meta:
        verbose_name = _("Exchange Account")
        verbose_name_plural = _("Exchange Accounts")
        unique_together = ("owner", "exchange", "label") # تغییر: owner به جای user، از BaseOwnedModel
        indexes = [
            models.Index(fields=['owner', 'exchange', 'is_active']), # برای جستجوی سریع حساب‌های کاربر
            models.Index(fields=['exchange', 'is_active']), # برای جستجوی حساب‌های یک صرافی
        ]

    def __str__(self):
        return f"{self.owner.email} - {self.exchange.name} ({self.label or 'Default'})" # تغییر: owner به جای user

    # متدهای کمکی برای کار با کلیدهای رمزنگاری شده
    @property
    def api_key(self):
        """Decrypts and returns the API key."""
        return decrypt_field(self._api_key_encrypted, self.encrypted_key_iv)

    @api_key.setter
    def api_key(self, value):
        """Encrypts and stores the API key."""
        encrypted_val, iv = encrypt_field(value)
        self._api_key_encrypted = encrypted_val
        self.encrypted_key_iv = iv # فقط در صورت نیاز به IV جداگانه برای هر کلید

    @property
    def api_secret(self):
        """Decrypts and returns the API secret."""
        return decrypt_field(self._api_secret_encrypted, self.encrypted_key_iv)

    @api_secret.setter
    def api_secret(self, value):
        """Encrypts and stores the API secret."""
        encrypted_val, iv = encrypt_field(value)
        self._api_secret_encrypted = encrypted_val
        # IV ممکن است یکی برای هر جفت کلید/مخفی باشد، یا جداگانه ذخیره شود، بسته به پیاده‌سازی

    def clean(self):
        """
        Validates the model instance.
        """
        super().clean()
        # اعتبارسنجی IPها (اگر وجود داشته باشند)
        if self.created_ip:
            try:
                # تابع validate_ip_list از core.helpers استفاده می‌شود
                from ipaddress import ip_address
                ip_address(self.created_ip)
            except ValueError:
                raise ValidationError({'created_ip': _('Invalid IP address format.')})

        if self.last_login_ip:
            from ipaddress import ip_address
            try:
                ip_address(self.last_login_ip)
            except ValueError:
                raise ValidationError({'last_login_ip': _('Invalid IP address format.')})

        # اعتبارسنجی extra_credentials (اگر نیاز باشد)
        if self.extra_credentials:
            # مثال: چک کردن ساختار JSON یا محتوای خاص
            if not isinstance(self.extra_credentials, dict):
                raise ValidationError({'extra_credentials': _('Must be a valid JSON object.')})
            # مثال: چک کردن وجود فیلد خاص
            # if 'required_field' not in self.extra_credentials:
            #     raise ValidationError({'extra_credentials': _('Missing required field: required_field')})

        # اعتبارسنجی فیلدهای مرتبط با مارجین
        if self.initial_margin_ratio and self.maintenance_margin_ratio and self.initial_margin_ratio < self.maintenance_margin_ratio:
            raise ValidationError({'initial_margin_ratio': _('Initial margin ratio cannot be less than maintenance margin ratio.')})

        if self.max_leverage and self.max_leverage < 1:
            raise ValidationError({'max_leverage': _('Max leverage must be at least 1.')})

    # --- منطق مربوط به اتصال ---
    def connect_to_exchange(self):
        """
        Connects to the exchange using the stored credentials.
        This would typically involve using a connector service.
        """
        try:
            from apps.connectors.service import ConnectorService # import داخل تابع برای جلوگیری از حلقه
            connector = ConnectorService(self.exchange.name)
            connection = connector.connect(
                api_key=self.api_key, # از property رمزنگاری شده استفاده می‌کند
                api_secret=self.api_secret, # از property رمزنگاری شده استفاده می‌کند
                extra_creds=self.extra_credentials
            )
            return connection
        except Exception as e:
            logger.error(f"Failed to connect to exchange {self.exchange.name} for account {self.label}: {str(e)}")
            raise # یا مدیریت خطا مناسب


class Wallet(BaseModel): # این مدل ممکن است مالکیت مستقیم نداشته باشد، فقط مربوط به یک ExchangeAccount است
    """
    تعریف انواع کیف پول در یک حساب صرافی (Spot, Futures, ...).
    """
    WALLET_TYPE_CHOICES = [
        ("SPOT", _("Spot")),
        ("FUTURES", _("Futures")),
        ("MARGIN", _("Margin")),
        ("ISOLATED_MARGIN", _("Isolated Margin")),
        ("FUNDING", _("Funding")),
        ("OTHER", _("Other")),
    ]
    exchange_account = models.ForeignKey(
        "exchanges.ExchangeAccount", # استفاده از نام اپلیکیشن
        on_delete=models.CASCADE,
        related_name="wallets",
        verbose_name=_("Exchange Account")
    )
    wallet_type = models.CharField(max_length=16, choices=WALLET_TYPE_CHOICES, verbose_name=_("Wallet Type"))
    description = models.CharField(max_length=256, blank=True, verbose_name=_("Description"))
    is_default = models.BooleanField(default=False, verbose_name=_("Is Default Wallet"))
    # ویژگی‌های مربوط به مارجین و لوریج
    is_margin_enabled = models.BooleanField(default=False, verbose_name=_("Is Margin Enabled"))
    leverage = models.DecimalField(max_digits=5, decimal_places=2, default=1, verbose_name=_("Leverage"))
    borrowed_amount = models.DecimalField(max_digits=32, decimal_places=16, default=0, verbose_name=_("Borrowed Amount"))

    class Meta:
        verbose_name = _("Wallet")
        verbose_name_plural = _("Wallets")
        unique_together = ("exchange_account", "wallet_type") # یک کاربر فقط یک کیف پول از هر نوع در یک صرافی دارد
        indexes = [
            models.Index(fields=['exchange_account', 'wallet_type']),
        ]

    def __str__(self):
        return f"{self.exchange_account.owner.email} - {self.exchange_account.exchange.name} - {self.wallet_type}" # تغییر: owner به جای user


class WalletBalance(BaseModel):
    """
    نگهداری موجودی هر ارز در هر کیف پول.
    """
    wallet = models.ForeignKey(
        "exchanges.Wallet",
        on_delete=models.CASCADE,
        related_name="balances",
        verbose_name=_("Wallet")
    )
    asset_symbol = models.CharField(max_length=32, verbose_name=_("Asset Symbol"))  # e.g. BTC, USDT
    total_balance = models.DecimalField(max_digits=32, decimal_places=16, default=0, verbose_name=_("Total Balance"))
    available_balance = models.DecimalField(max_digits=32, decimal_places=16, default=0, verbose_name=_("Available Balance"))
    in_order_balance = models.DecimalField(max_digits=32, decimal_places=16, default=0, verbose_name=_("Balance in Orders"))
    frozen_balance = models.DecimalField(max_digits=32, decimal_places=16, default=0, verbose_name=_("Frozen Balance"))
    borrowed_balance = models.DecimalField(max_digits=32, decimal_places=16, default=0, verbose_name=_("Borrowed Balance"))

    # فیلدهای timestamp از BaseModel ارث می‌بریم: created_at, updated_at

    class Meta:
        verbose_name = _("Wallet Balance")
        verbose_name_plural = _("Wallet Balances")
        unique_together = ("wallet", "asset_symbol") # یک ارز فقط یک بار در یک کیف پول وجود داشته باشد
        indexes = [
            models.Index(fields=['wallet', 'asset_symbol']),
        ]

    def __str__(self):
        return f"{self.asset_symbol}: {self.available_balance} ({self.wallet})"


class AggregatedPortfolio(BaseOwnedModel): # استفاده از BaseOwnedModel از core
    """
    نگهداری پرتفوی کلی و تجمیعی کاربر.
    """
    base_currency = models.CharField(max_length=16, default="USD", verbose_name=_("Base Currency"))
    total_equity = models.DecimalField(max_digits=32, decimal_places=8, default=0, verbose_name=_("Total Equity"))
    total_unrealized_pnl = models.DecimalField(max_digits=32, decimal_places=8, default=0, verbose_name=_("Total Unrealized PnL"))
    total_realized_pnl = models.DecimalField(max_digits=32, decimal_places=8, default=0, verbose_name=_("Total Realized PnL"))
    total_pnl_percentage = models.DecimalField(max_digits=8, decimal_places=4, default=0, verbose_name=_("Total PnL Percentage"))
    total_commission_paid = models.DecimalField(max_digits=32, decimal_places=8, default=0, verbose_name=_("Total Commission Paid"))
    total_funding_fees = models.DecimalField(max_digits=32, decimal_places=8, default=0, verbose_name=_("Total Funding Fees"))
    last_valuation_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Valuation At"))

    # فیلدهای timestamp از BaseModel (که در BaseOwnedModel ارث می‌برد) ارث می‌بریم: created_at, updated_at

    class Meta:
        verbose_name = _("Aggregated Portfolio")
        verbose_name_plural = _("Aggregated Portfolios")

    def __str__(self):
        return f"Portfolio of {self.owner.email}" # تغییر: owner به جای user


class AggregatedAssetPosition(BaseModel): # این مدل مربوط به یک AggregatedPortfolio است، نه مستقیماً کاربر
    """
    نگهداری پوزیشن تجمیعی هر دارایی برای کاربر در سطح کل پرتفوی.
    """
    aggregated_portfolio = models.ForeignKey(
        "exchanges.AggregatedPortfolio", # استفاده از نام اپلیکیشن
        on_delete=models.CASCADE,
        related_name="asset_positions",
        verbose_name=_("Aggregated Portfolio")
    )
    asset_symbol = models.CharField(max_length=32, verbose_name=_("Asset Symbol"))  # e.g. BTC, USDT
    total_quantity = models.DecimalField(max_digits=32, decimal_places=16, default=0, verbose_name=_("Total Quantity"))
    total_value_in_base_currency = models.DecimalField(max_digits=32, decimal_places=8, default=0, verbose_name=_("Total Value in Base Currency"))
    # تفکیک بر اساس صرافی (JSON)
    per_exchange_breakdown = models.JSONField(default=dict, verbose_name=_("Per Exchange Breakdown (JSON)"))

    # فیلدهای timestamp از BaseModel ارث می‌بریم: created_at, updated_at

    class Meta:
        verbose_name = _("Aggregated Asset Position")
        verbose_name_plural = _("Aggregated Asset Positions")
        unique_together = ("aggregated_portfolio", "asset_symbol") # یک ارز فقط یک بار در یک پرتفوی تجمیعی وجود داشته باشد
        indexes = [
            models.Index(fields=['aggregated_portfolio', 'asset_symbol']),
        ]

    def __str__(self):
        return f"{self.asset_symbol} in Portfolio of {self.aggregated_portfolio.owner.email}" # تغییر: owner به جای user


# --- مدل‌های مربوط به تاریخچه معاملات و داده بازار ---
# این مدل‌ها ممکن است بیشتر جایشان در اپلیکیشن `trading` یا `market_data` باشد
# اما اگر فقط مربوط به حساب صرافی کاربر است، می‌توانند در `exchanges` بمانند

class OrderHistory(BaseModel):
    """
    تاریخچه معاملات (سفارشات) انجام شده از طریق حساب‌های صرافی.
    """
    STATUS_CHOICES = [
        ('NEW', _('New')),
        ('PARTIALLY_FILLED', _('Partially Filled')),
        ('FILLED', _('Filled')),
        ('CANCELED', _('Canceled')),
        ('PENDING_CANCEL', _('Pending Cancel')),
        ('REJECTED', _('Rejected')),
        ('EXPIRED', _('Expired')),
    ]
    SIDE_CHOICES = [
        ('BUY', _('Buy')),
        ('SELL', _('Sell')),
    ]
    ORDER_TYPE_CHOICES = [
        ('LIMIT', _('Limit')),
        ('MARKET', _('Market')),
        ('STOP_LOSS', _('Stop Loss')),
        ('TAKE_PROFIT', _('Take Profit')),
        # سایر نوع‌های سفارش صرافی
    ]
    exchange_account = models.ForeignKey(
        ExchangeAccount, # استفاده از مدل تعریف شده در همین اپلیکیشن
        on_delete=models.CASCADE,
        related_name="order_history",
        verbose_name=_("Exchange Account")
    )
    order_id = models.CharField(max_length=255, verbose_name=_("Exchange Order ID")) # شناسه منحصر به فرد سفارش در صرافی
    symbol = models.CharField(max_length=32, verbose_name=_("Symbol"))
    side = models.CharField(max_length=10, choices=SIDE_CHOICES, verbose_name=_("Side"))
    order_type = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES, verbose_name=_("Order Type"))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name=_("Status"))
    price = models.DecimalField(max_digits=32, decimal_places=16, verbose_name=_("Price"))
    quantity = models.DecimalField(max_digits=32, decimal_places=16, verbose_name=_("Quantity"))
    executed_quantity = models.DecimalField(max_digits=32, decimal_places=16, default=0, verbose_name=_("Executed Quantity"))
    cumulative_quote_qty = models.DecimalField(max_digits=32, decimal_places=16, default=0, verbose_name=_("Cumulative Quote Quantity"))
    time_placed = models.DateTimeField(verbose_name=_("Time Placed"))
    time_updated = models.DateTimeField(verbose_name=_("Time Updated"))
    commission = models.DecimalField(max_digits=32, decimal_places=16, default=0, verbose_name=_("Commission"))
    commission_asset = models.CharField(max_length=32, verbose_name=_("Commission Asset"))
    # ارتباط با بات (اختیاری)
    trading_bot = models.ForeignKey(
        TradingBot,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="executed_orders_linked", # نام related_name باید منحصر به فرد باشد
        verbose_name=_("Trading Bot")
    )

    class Meta:
        verbose_name = _("Order History")
        verbose_name_plural = _("Order Histories")
        unique_together = ("exchange_account", "order_id") # هر سفارش در یک حساب صرافی منحصر به فرد است
        indexes = [
            models.Index(fields=['exchange_account', 'time_placed']), # برای جستجوی تاریخچه
            models.Index(fields=['symbol', 'time_placed']), # برای تحلیل نماد
            models.Index(fields=['status', 'time_updated']), # برای فیلتر سفارشات فعال/به‌روزرسانی شده
        ]

    def __str__(self):
        return f"{self.side} {self.quantity} {self.symbol} ({self.status}) on {self.exchange_account}"


class MarketDataCandle(BaseModel): # این مدل بیشتر مربوط به market_data است، اما اگر فقط برای تاریخچه یا نمایش ساده در exchanges نیاز باشد
    """
    مدل ذخیره‌سازی داده‌های کندل (OHLCV) از صرافی‌ها برای بک تست و تحلیل.
    این مدل ممکن است در اپلیکیشن 'market_data' منطقی‌تر باشد.
    """
    INTERVAL_CHOICES = [
        ('1m', _('1 Minute')),
        ('5m', _('5 Minutes')),
        ('15m', _('15 Minutes')),
        ('30m', _('30 Minutes')),
        ('1h', _('1 Hour')),
        ('4h', _('4 Hours')),
        ('1d', _('1 Day')),
        ('1w', _('1 Week')),
        ('1M', _('1 Month')),
    ]
    exchange = models.ForeignKey(
        Exchange, # استفاده از مدل تعریف شده در همین اپلیکیشن
        on_delete=models.CASCADE,
        related_name="candle_data",
        verbose_name=_("Exchange")
    )
    symbol = models.CharField(max_length=32, verbose_name=_("Symbol"))
    interval = models.CharField(max_length=10, choices=INTERVAL_CHOICES, verbose_name=_("Interval"))
    open_time = models.DateTimeField(verbose_name=_("Open Time"))
    open = models.DecimalField(max_digits=32, decimal_places=16, verbose_name=_("Open Price"))
    high = models.DecimalField(max_digits=32, decimal_places=16, verbose_name=_("High Price"))
    low = models.DecimalField(max_digits=32, decimal_places=16, verbose_name=_("Low Price"))
    close = models.DecimalField(max_digits=32, decimal_places=16, verbose_name=_("Close Price"))
    volume = models.DecimalField(max_digits=32, decimal_places=16, verbose_name=_("Volume"))
    close_time = models.DateTimeField(verbose_name=_("Close Time"))
    quote_asset_volume = models.DecimalField(max_digits=32, decimal_places=16, verbose_name=_("Quote Asset Volume"))
    number_of_trades = models.IntegerField(verbose_name=_("Number of Trades"))
    taker_buy_base_asset_volume = models.DecimalField(max_digits=32, decimal_places=16, verbose_name=_("Taker Buy Base Asset Volume"))
    taker_buy_quote_asset_volume = models.DecimalField(max_digits=32, decimal_places=16, verbose_name=_("Taker Buy Quote Asset Volume"))

    class Meta:
        verbose_name = _("Market Data Candle")
        verbose_name_plural = _("Market Data Candles")
        unique_together = ("exchange", "symbol", "interval", "open_time") # یک کندل منحصر به فرد
        indexes = [
            models.Index(fields=['exchange', 'symbol', 'interval', 'open_time']), # برای جستجوی کارآمد
            models.Index(fields=['symbol', 'open_time']), # برای تحلیل نماد
        ]

    def __str__(self):
        return f"{self.symbol} - {self.interval} - {self.open_time}"

# --- مدل‌های دیگر ---
# می‌توانید مدل‌های دیگری که مربوط به اطلاعات صرافی یا حساب‌های صرافی است اضافه کنید
# مثلاً یک مدل برای تاریخچه تراز صرافی (Balance History)
# یا یک مدل برای نگاشت نمادهای صرافی به نمادهای داخلی (Symbol Mapping)
# یا یک مدل برای مدیریت کانفیگ‌های اتصال خاص هر صرافی (ExchangeConfig)
# یا یک مدل برای لاگ اتصالات (ConnectionLog)

# class ExchangeConnectionLog(BaseModel):
#     exchange_account = models.ForeignKey(ExchangeAccount, on_delete=models.CASCADE, related_name="connection_logs")
#     status = models.CharField(max_length=16, choices=[('CONNECTED', 'Connected'), ('DISCONNECTED', 'Disconnected')])
#     reason = models.TextField(blank=True)
#     connected_at = models.DateTimeField(null=True, blank=True)
#     disconnected_at = models.DateTimeField(null=True, blank=True)
#     class Meta:
#         verbose_name = _("Exchange Connection Log")
#         verbose_name_plural = _("Exchange Connection Logs")
#         indexes = [
#             models.Index(fields=['exchange_account', '-connected_at']),
#         ]
#     def __str__(self):
#         return f"Connection Log for {self.exchange_account} - {self.status}"

logger.info("Exchanges models loaded successfully.")
