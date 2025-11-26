
# apps/exchanges/models.py
from django.db import models
from django.conf import settings

class Exchange(models.Model):
    """برای تعریف صرافی‌ها (مثلاً: Binance, Coinbase)"""
    EXCHANGE_TYPE_CHOICES = [
        ("CRYPTO", "Crypto Exchange"),
        ("STOCK", "Stock Broker"),
        ("FOREX", "Forex Broker"),
    ]
    name = models.CharField(max_length=128)
    code = models.CharField(max_length=32, unique=True)
    type = models.CharField(max_length=16, choices=EXCHANGE_TYPE_CHOICES)
    base_url = models.URLField()
    ws_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class ExchangeAccount(models.Model):
    """برای اتصال حساب کاربر به یک صرافی خاص"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="exchange_accounts")
    exchange = models.ForeignKey("exchanges.Exchange", on_delete=models.CASCADE, related_name="accounts")
    label = models.CharField(max_length=128, blank=True)

    api_key_encrypted = models.TextField()  # کلید API باید رمزنگاری شود
    api_secret_encrypted = models.TextField() # کلید Secret باید رمزنگاری شود
    extra_credentials = models.JSONField(default=dict, blank=True)

    is_active = models.BooleanField(default=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "exchange", "label")

    def __str__(self):
        return f"{self.user.email} - {self.exchange.name}"

class Wallet(models.Model):
    """برای تعریف انواع کیف پول در یک حساب صرافی (Spot, Futures, ...)"""
    WALLET_TYPE_CHOICES = [
        ("SPOT", "Spot"),
        ("FUTURES", "Futures"),
        ("MARGIN", "Margin"),
        ("OTHER", "Other"),
    ]
    exchange_account = models.ForeignKey("exchanges.ExchangeAccount", on_delete=models.CASCADE, related_name="wallets")
    wallet_type = models.CharField(max_length=16, choices=WALLET_TYPE_CHOICES)
    description = models.CharField(max_length=256, blank=True)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.exchange_account} - {self.wallet_type}"

class WalletBalance(models.Model):
    """برای نگهداری موجودی هر ارز در هر کیف پول"""
    wallet = models.ForeignKey("exchanges.Wallet", on_delete=models.CASCADE, related_name="balances")
    asset_symbol = models.CharField(max_length=32) # e.g. BTC, USDT
    total_balance = models.DecimalField(max_digits=32, decimal_places=16, default=0)
    available_balance = models.DecimalField(max_digits=32, decimal_places=16, default=0)
    in_order_balance = models.DecimalField(max_digits=32, decimal_places=16, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("wallet", "asset_symbol")

    def __str__(self):
        return f"{self.asset_symbol}: {self.available_balance}"

class AggregatedPortfolio(models.Model):
    """برای نگهداری پرتفوی کلی و تجمیعی کاربر"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="aggregated_portfolio")
    base_currency = models.CharField(max_length=16, default="USD")
    total_equity = models.DecimalField(max_digits=32, decimal_places=8, default=0)
    total_unrealized_pnl = models.DecimalField(max_digits=32, decimal_places=8, default=0)
    total_realized_pnl = models.DecimalField(max_digits=32, decimal_places=8, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Portfolio of {self.user.email}"