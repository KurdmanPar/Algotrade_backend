# apps/trading/admin.py
from django.contrib import admin
from .models import Order, Trade, Position, OrderLog

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('client_order_id', 'user', 'instrument', 'side', 'order_type', 'quantity', 'price', 'status', 'created_at')
    list_filter = ('status', 'side', 'order_type', 'created_at')
    raw_id_fields = ('user', 'exchange_account', 'instrument', 'bot', 'signal', 'risk_profile', 'agent')

@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ('order', 'trade_id', 'price', 'quantity', 'executed_at')
    list_filter = ('executed_at',)
    raw_id_fields = ('order', 'agent', 'strategy_version')

@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('user', 'instrument', 'side', 'quantity', 'avg_entry_price', 'status', 'opened_at')
    list_filter = ('side', 'status', 'opened_at')
    raw_id_fields = ('user', 'exchange_account', 'instrument', 'bot', 'agent', 'strategy_version')

@admin.register(OrderLog)
class OrderLogAdmin(admin.ModelAdmin):
    list_display = ('order', 'old_status', 'new_status', 'created_at')
    list_filter = ('new_status', 'created_at')
    raw_id_fields = ('order',)
