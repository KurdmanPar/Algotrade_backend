# apps/trading/models.py
from django.db import models
from django.conf import settings
from apps.core.models import BaseModel

class Order(BaseModel):
    """برای نگهداری سفارشات ارسال شده به صرافی"""
    SIDE_CHOICES = [("BUY", "Buy"), ("SELL", "Sell")]
    ORDER_TYPE_CHOICES = [("MARKET", "Market"), ("LIMIT", "Limit"), ("STOP", "Stop"), ("STOP_LIMIT", "Stop Limit")]
    STATUS_CHOICES = [("NEW", "New"), ("PARTIALLY_FILLED", "Partially Filled"), ("FILLED", "Filled"), ("CANCELED", "Canceled"), ("REJECTED", "Rejected")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    exchange_account = models.ForeignKey("exchanges.ExchangeAccount", on_delete=models.PROTECT, related_name="orders")
    # این فیلد به صورت موقت است و بعداً به مدل Instrument لینک می‌شود
    instrument_symbol = models.CharField(max_length=64, help_text="e.g., BTCUSDT")

    side = models.CharField(max_length=8, choices=SIDE_CHOICES)
    order_type = models.CharField(max_length=16, choices=ORDER_TYPE_CHOICES)
    quantity = models.DecimalField(max_digits=32, decimal_places=16)
    price = models.DecimalField(max_digits=32, decimal_places=16, null=True, blank=True)
    time_in_force = models.CharField(max_length=16, default="GTC")

    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="NEW")
    client_order_id = models.CharField(max_length=64, unique=True)
    exchange_order_id = models.CharField(max_length=64, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.side} {self.quantity} {self.instrument_symbol}"

class Trade(models.Model):
    """برای نگهداری معاملات انجام شده (پر شده)"""
    order = models.ForeignKey("trading.Order", on_delete=models.CASCADE, related_name="trades")
    trade_id = models.CharField(max_length=64, blank=True)
    price = models.DecimalField(max_digits=32, decimal_places=16)
    quantity = models.DecimalField(max_digits=32, decimal_places=16)
    fee = models.DecimalField(max_digits=32, decimal_places=16, default=0)
    fee_asset = models.CharField(max_length=32, blank=True)
    executed_at = models.DateTimeField()

    def __str__(self):
        return f"Trade {self.trade_id} for {self.quantity} @ {self.price}"

class Position(models.Model):
    """برای نگهداری پوزیشن‌های باز یا بسته شده"""
    SIDE_CHOICES = [("LONG", "Long"), ("SHORT", "Short")]
    STATUS_CHOICES = [("OPEN", "Open"), ("CLOSED", "Closed")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="positions")
    exchange_account = models.ForeignKey("exchanges.ExchangeAccount", on_delete=models.PROTECT, related_name="positions")
    # این فیلد به صورت موقت است و بعداً به مدل Instrument لینک می‌شود
    instrument_symbol = models.CharField(max_length=64, help_text="e.g., BTCUSDT")

    side = models.CharField(max_length=8, choices=SIDE_CHOICES)
    quantity = models.DecimalField(max_digits=32, decimal_places=16)
    avg_entry_price = models.DecimalField(max_digits=32, decimal_places=16)

    unrealized_pnl = models.DecimalField(max_digits=32, decimal_places=8, default=0)
    realized_pnl = models.DecimalField(max_digits=32, decimal_places=8, default=0)

    opened_at = models.DateTimeField()
    closed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="OPEN")

    def __str__(self):
        return f"{self.side} {self.quantity} {self.instrument_symbol} ({self.status})"
