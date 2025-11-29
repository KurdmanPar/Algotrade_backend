# apps/trading/models.py
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel


class Order(BaseModel):
    SIDE_CHOICES = [
        ("BUY", _("Buy")),
        ("SELL", _("Sell")),
    ]
    ORDER_TYPE_CHOICES = [
        ("MARKET", _("Market")),
        ("LIMIT", _("Limit")),
        ("STOP", _("Stop")),
        ("STOP_LIMIT", _("Stop Limit")),
        ("TAKE_PROFIT", _("Take Profit")),
        ("TAKE_PROFIT_LIMIT", _("Take Profit Limit")),
        ("TRAILING_STOP", _("Trailing Stop")),
    ]
    STATUS_CHOICES = [
        ("NEW", _("New")),
        ("PARTIALLY_FILLED", _("Partially Filled")),
        ("FILLED", _("Filled")),
        ("CANCELED", _("Canceled")),
        ("REJECTED", _("Rejected")),
        ("EXPIRED", _("Expired")),
    ]
    TIME_IN_FORCE_CHOICES = [
        ("GTC", _("Good Till Canceled")),
        ("IOC", _("Immediate or Cancel")),
        ("FOK", _("Fill or Kill")),
        ("GTX", _("Good Till Crossing")),
        ("GTD", _("Good Till Date")),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name=_("User")
    )
    exchange_account = models.ForeignKey(
        "exchanges.ExchangeAccount",
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name=_("Exchange Account")
    )
    instrument = models.ForeignKey(
        "instruments.Instrument",
        on_delete=models.PROTECT,
        related_name="orders",
        verbose_name=_("Instrument")
    )
    bot = models.ForeignKey(
        "bots.Bot",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name=_("Bot")
    )
    signal = models.ForeignKey(
        "signals.Signal",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name=_("Signal")
    )
    risk_profile = models.ForeignKey(
        "risk.RiskProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name=_("Risk Profile")
    )
    agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="orders",
        verbose_name=_("Agent (MAS)")
    )

    side = models.CharField(max_length=8, choices=SIDE_CHOICES, verbose_name=_("Side"))
    order_type = models.CharField(max_length=17, choices=ORDER_TYPE_CHOICES, verbose_name=_("Order Type"))  # تغییر max_length
    quantity = models.DecimalField(max_digits=32, decimal_places=16, verbose_name=_("Quantity"))
    price = models.DecimalField(max_digits=32, decimal_places=16, null=True, blank=True, verbose_name=_("Price"))
    stop_price = models.DecimalField(max_digits=32, decimal_places=16, null=True, blank=True, verbose_name=_("Stop Price"))
    time_in_force = models.CharField(max_length=16, choices=TIME_IN_FORCE_CHOICES, default="GTC", verbose_name=_("Time in Force"))

    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="NEW", verbose_name=_("Status"))
    client_order_id = models.CharField(max_length=64, unique=True, verbose_name=_("Client Order ID"))
    exchange_order_id = models.CharField(max_length=64, blank=True, verbose_name=_("Exchange Order ID"))

    commission_paid = models.DecimalField(max_digits=32, decimal_places=16, default=0, verbose_name=_("Commission Paid"))
    stop_loss_price = models.DecimalField(max_digits=32, decimal_places=16, null=True, blank=True, verbose_name=_("Stop Loss Price"))
    take_profit_price = models.DecimalField(max_digits=32, decimal_places=16, null=True, blank=True, verbose_name=_("Take Profit Price"))

    correlation_id = models.CharField(max_length=64, blank=True, verbose_name=_("Correlation ID"))

    def __str__(self):
        return f"{self.side} {self.quantity} {self.instrument.symbol} ({self.status})"

    class Meta:
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")
        indexes = [
            models.Index(fields=['client_order_id']),
            models.Index(fields=['exchange_order_id']),
            models.Index(fields=['user', '-created_at']),
        ]


class Trade(BaseModel):
    order = models.ForeignKey(
        "trading.Order",
        on_delete=models.CASCADE,
        related_name="trades",
        verbose_name=_("Order")
    )
    agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trades",
        verbose_name=_("Agent (MAS)")
    )
    trade_id = models.CharField(max_length=64, verbose_name=_("Trade ID"))
    price = models.DecimalField(max_digits=32, decimal_places=16, verbose_name=_("Price"))
    quantity = models.DecimalField(max_digits=32, decimal_places=16, verbose_name=_("Quantity"))
    fee = models.DecimalField(max_digits=32, decimal_places=16, default=0, verbose_name=_("Fee"))
    fee_asset = models.CharField(max_length=32, blank=True, verbose_name=_("Fee Asset"))
    executed_at = models.DateTimeField(verbose_name=_("Executed At"))

    strategy_version = models.ForeignKey(
        "strategies.StrategyVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Strategy Version")
    )
    source_event = models.CharField(max_length=64, blank=True, verbose_name=_("Source Event"))

    correlation_id = models.CharField(max_length=64, blank=True, verbose_name=_("Correlation ID"))

    def __str__(self):
        return f"Trade {self.trade_id} for {self.quantity} @ {self.price}"

    class Meta:
        verbose_name = _("Trade")
        verbose_name_plural = _("Trades")
        unique_together = ("order", "trade_id")
        indexes = [
            models.Index(fields=['executed_at', 'order']),
        ]


class Position(BaseModel):
    SIDE_CHOICES = [
        ("LONG", _("Long")),
        ("SHORT", _("Short")),
    ]
    STATUS_CHOICES = [
        ("OPEN", _("Open")),
        ("CLOSED", _("Closed")),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="positions",
        verbose_name=_("User")
    )
    exchange_account = models.ForeignKey(
        "exchanges.ExchangeAccount",
        on_delete=models.PROTECT,
        related_name="positions",
        verbose_name=_("Exchange Account")
    )
    instrument = models.ForeignKey(
        "instruments.Instrument",
        on_delete=models.PROTECT,
        related_name="positions",
        verbose_name=_("Instrument")
    )
    bot = models.ForeignKey(
        "bots.Bot",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="positions",
        verbose_name=_("Bot")
    )
    agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="positions",
        verbose_name=_("Agent (MAS)")
    )
    strategy_version = models.ForeignKey(
        "strategies.StrategyVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Strategy Version")
    )

    side = models.CharField(max_length=8, choices=SIDE_CHOICES, verbose_name=_("Side"))
    quantity = models.DecimalField(max_digits=32, decimal_places=16, verbose_name=_("Quantity"))
    avg_entry_price = models.DecimalField(max_digits=32, decimal_places=16, verbose_name=_("Average Entry Price"))

    leverage = models.DecimalField(max_digits=5, decimal_places=2, default=1, verbose_name=_("Leverage"))
    liquidation_price = models.DecimalField(max_digits=32, decimal_places=16, null=True, blank=True, verbose_name=_("Liquidation Price"))
    margin_used = models.DecimalField(max_digits=32, decimal_places=16, default=0, verbose_name=_("Margin Used"))

    unrealized_pnl = models.DecimalField(max_digits=32, decimal_places=8, default=0, verbose_name=_("Unrealized P&L"))
    realized_pnl = models.DecimalField(max_digits=32, decimal_places=8, default=0, verbose_name=_("Realized P&L"))

    opened_at = models.DateTimeField(verbose_name=_("Opened At"))
    closed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Closed At"))
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="OPEN", verbose_name=_("Status"))

    entry_trades = models.ManyToManyField("trading.Trade", related_name="entry_positions", verbose_name=_("Entry Trades"))
    exit_trades = models.ManyToManyField("trading.Trade", related_name="exit_positions", blank=True, verbose_name=_("Exit Trades"))

    def __str__(self):
        return f"{self.side} {self.quantity} {self.instrument.symbol} ({self.status})"

    class Meta:
        verbose_name = _("Position")
        verbose_name_plural = _("Positions")
        indexes = [
            models.Index(fields=['user', 'status', '-opened_at']),
        ]


class OrderLog(BaseModel):
    order = models.ForeignKey(
        "trading.Order",
        on_delete=models.CASCADE,
        related_name="status_logs",
        verbose_name=_("Order")
    )
    old_status = models.CharField(max_length=32, verbose_name=_("Old Status"))
    new_status = models.CharField(max_length=32, verbose_name=_("New Status"))
    message = models.TextField(blank=True, verbose_name=_("Log Message"))
    details = models.JSONField(default=dict, blank=True, verbose_name=_("Details (JSON)"))

    def __str__(self):
        return f"Order {self.order.client_order_id} changed from {self.old_status} to {self.new_status}"

    class Meta:
        verbose_name = _("Order Log")
        verbose_name_plural = _("Order Logs")
        indexes = [
            models.Index(fields=['order', '-created_at']),
        ]