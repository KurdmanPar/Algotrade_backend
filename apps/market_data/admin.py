# apps/market_data/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    DataSource,
    MarketDataConfig,
    MarketDataSnapshot,
    MarketDataOrderBook,
    MarketDataTick,
    MarketDataSyncLog,
    MarketDataCache,
)


class DataSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'is_active', 'is_sandbox', 'rate_limit_per_minute', 'created_at')
    list_filter = ('type', 'is_active', 'is_sandbox', 'created_at')
    search_fields = ('name', 'type')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {'fields': ('name', 'type', 'is_active', 'is_sandbox')}),
        ('API Information', {
            'classes': ('collapse',),
            'fields': ('base_url', 'ws_url', 'api_docs_url'),
        }),
        ('Limits & Configuration', {
            'classes': ('collapse',),
            'fields': ('rate_limit_per_minute', 'supported_timeframes', 'supported_data_types', 'config'),
        }),
        ('Meta', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

admin.site.register(DataSource, DataSourceAdmin)


class MarketDataConfigAdmin(admin.ModelAdmin):
    list_display = ('instrument_symbol', 'data_source_name', 'timeframe', 'data_type', 'is_realtime', 'is_historical', 'status', 'last_sync_at', 'created_at')
    list_filter = ('data_source__name', 'timeframe', 'data_type', 'is_realtime', 'is_historical', 'status', 'created_at')
    search_fields = ('instrument__symbol', 'data_source__name')
    raw_id_fields = ('instrument', 'data_source') # برای انتخاب کارآمد
    readonly_fields = ('created_at', 'updated_at', 'last_sync_at')
    fieldsets = (
        (None, {'fields': ('instrument', 'data_source', 'timeframe', 'data_type')}),
        ('Sync Settings', {'fields': ('is_realtime', 'is_historical', 'storage_backend', 'collection_or_table_name')}),
        ('Status & Limits', {'fields': ('depth_levels', 'include_additional_fields', 'status', 'last_sync_at')}),
        ('Meta', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    def instrument_symbol(self, obj):
        return obj.instrument.symbol
    instrument_symbol.short_description = 'Instrument'
    instrument_symbol.admin_order_field = 'instrument__symbol'

    def data_source_name(self, obj):
        return obj.data_source.name
    data_source_name.short_description = 'Data Source'
    data_source_name.admin_order_field = 'data_source__name'

admin.site.register(MarketDataConfig, MarketDataConfigAdmin)


class MarketDataSnapshotAdmin(admin.ModelAdmin):
    list_display = ('config_instrument', 'timestamp', 'open_price', 'high_price', 'low_price', 'close_price', 'volume', 'updated_at')
    list_filter = ('config__instrument__symbol', 'config__data_source__name', 'config__timeframe', 'timestamp', 'updated_at')
    search_fields = ('config__instrument__symbol', 'config__data_source__name', 'timestamp')
    raw_id_fields = ('config',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp'] # جدیدترین اول
    fieldsets = (
        (None, {'fields': ('config', 'timestamp')}),
        ('OHLCV Data', {'fields': ('open_price', 'high_price', 'low_price', 'close_price')}),
        ('Volume & Advanced', {'fields': ('volume', 'quote_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume')}),
        ('Order Book Related', {'fields': ('best_bid', 'best_ask', 'bid_size', 'ask_size')}),
        ('Meta', {
            'classes': ('collapse',),
            'fields': ('additional_data', 'created_at', 'updated_at'),
        }),
    )

    def config_instrument(self, obj):
        return f"{obj.config.instrument.symbol} ({obj.config.timeframe})"
    config_instrument.short_description = 'Instrument (TF)'
    config_instrument.admin_order_field = 'config__instrument__symbol'

admin.site.register(MarketDataSnapshot, MarketDataSnapshotAdmin)


class MarketDataOrderBookAdmin(admin.ModelAdmin):
    list_display = ('config_instrument', 'timestamp', 'top_bid_price', 'top_ask_price', 'sequence', 'updated_at')
    list_filter = ('config__instrument__symbol', 'config__data_source__name', 'timestamp', 'updated_at')
    search_fields = ('config__instrument__symbol', 'timestamp', 'sequence')
    raw_id_fields = ('config',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    fieldsets = (
        (None, {'fields': ('config', 'timestamp', 'sequence', 'checksum')}),
        ('Order Book Data', {'fields': ('bids', 'asks')}),
        ('Meta', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    def config_instrument(self, obj):
        return f"{obj.config.instrument.symbol} ({obj.config.timeframe})"
    config_instrument.short_description = 'Instrument (TF)'

    def top_bid_price(self, obj):
        if obj.bids and len(obj.bids) > 0:
            return obj.bids[0][0] # اولین قیمت پیشنهاد خرید
        return "N/A"
    top_bid_price.short_description = 'Top Bid'

    def top_ask_price(self, obj):
        if obj.asks and len(obj.asks) > 0:
            return obj.asks[0][0] # اولین قیمت پیشنهاد فروش
        return "N/A"
    top_ask_price.short_description = 'Top Ask'

admin.site.register(MarketDataOrderBook, MarketDataOrderBookAdmin)


class MarketDataTickAdmin(admin.ModelAdmin):
    list_display = ('config_instrument', 'timestamp', 'price', 'quantity', 'side', 'updated_at')
    list_filter = ('config__instrument__symbol', 'config__data_source__name', 'side', 'timestamp', 'updated_at')
    search_fields = ('config__instrument__symbol', 'timestamp', 'trade_id')
    raw_id_fields = ('config',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'timestamp'
    ordering = ['-timestamp']
    fieldsets = (
        (None, {'fields': ('config', 'timestamp', 'trade_id')}),
        ('Tick Data', {'fields': ('price', 'quantity', 'side')}),
        ('Meta', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    def config_instrument(self, obj):
        return f"{obj.config.instrument.symbol} ({obj.config.timeframe})"
    config_instrument.short_description = 'Instrument (TF)'

admin.site.register(MarketDataTick, MarketDataTickAdmin)


class MarketDataSyncLogAdmin(admin.ModelAdmin):
    list_display = ('config_instrument', 'start_time', 'end_time', 'duration', 'status', 'records_synced', 'updated_at')
    list_filter = ('config__instrument__symbol', 'config__data_source__name', 'status', 'start_time', 'updated_at')
    search_fields = ('config__instrument__symbol', 'error_message')
    raw_id_fields = ('config',)
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'start_time'
    ordering = ['-start_time']
    fieldsets = (
        (None, {'fields': ('config', 'start_time', 'end_time', 'status', 'records_synced')}),
        ('Details', {'fields': ('error_message', 'details')}),
        ('Meta', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    def config_instrument(self, obj):
        return f"{obj.config.instrument.symbol} ({obj.config.timeframe})"
    config_instrument.short_description = 'Instrument (TF)'

    def duration(self, obj):
        if obj.end_time and obj.start_time:
            return obj.end_time - obj.start_time
        return "N/A"
    duration.short_description = 'Duration'

admin.site.register(MarketDataSyncLog, MarketDataSyncLogAdmin)


class MarketDataCacheAdmin(admin.ModelAdmin):
    list_display = ('config_instrument', 'cached_at', 'updated_at')
    list_filter = ('config__instrument__symbol', 'config__data_source__name', 'cached_at', 'updated_at')
    search_fields = ('config__instrument__symbol',)
    raw_id_fields = ('config',)
    readonly_fields = ('created_at', 'updated_at', 'cached_at')
    date_hierarchy = 'cached_at'
    ordering = ['-cached_at']
    fieldsets = (
        (None, {'fields': ('config', 'cached_at')}),
        ('Cached Data', {'fields': ('latest_snapshot',)}),
        ('Meta', {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at'),
        }),
    )

    def config_instrument(self, obj):
        return f"{obj.config.instrument.symbol} ({obj.config.timeframe})"
    config_instrument.short_description = 'Instrument (TF)'

admin.site.register(MarketDataCache, MarketDataCacheAdmin)
