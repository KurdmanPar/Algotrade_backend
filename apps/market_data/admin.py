# apps/market_data/admin.py
from django.contrib import admin
from .models import DataSource, MarketDataConfig, MarketDataSnapshot, MarketDataSyncLog

@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'is_active', 'rate_limit_per_minute')
    list_filter = ('type', 'is_active')
    search_fields = ('name', 'type')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(MarketDataConfig)
class MarketDataConfigAdmin(admin.ModelAdmin):
    list_display = ('instrument', 'data_source', 'timeframe', 'data_type', 'is_realtime', 'is_historical', 'status', 'last_sync_at')
    list_filter = ('data_type', 'is_realtime', 'is_historical', 'status', 'data_source')
    raw_id_fields = ('instrument', 'data_source', 'api_credential')
    search_fields = ('instrument__symbol', 'data_source__name')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(MarketDataSnapshot)
class MarketDataSnapshotAdmin(admin.ModelAdmin):
    list_display = ('get_instrument', 'get_timeframe', 'timestamp', 'open_price', 'close_price', 'volume')
    list_filter = ('timestamp', 'config__timeframe', 'config__data_source')
    raw_id_fields = ('config',)  # تغییر از 'instrument' به 'config'
    search_fields = ('config__instrument__symbol', 'config__data_source__name')
    date_hierarchy = 'timestamp'
    readonly_fields = ('created_at', 'updated_at')

    def get_instrument(self, obj):
        return obj.config.instrument.symbol if obj.config and obj.config.instrument else '-'
    get_instrument.short_description = 'Instrument'
    get_instrument.admin_order_field = 'config__instrument__symbol'

    def get_timeframe(self, obj):
        return obj.config.timeframe if obj.config else '-'
    get_timeframe.short_description = 'Timeframe'
    get_timeframe.admin_order_field = 'config__timeframe'

@admin.register(MarketDataSyncLog)
class MarketDataSyncLogAdmin(admin.ModelAdmin):
    list_display = ('config', 'start_time', 'end_time', 'status', 'records_synced')
    list_filter = ('status', 'start_time')
    raw_id_fields = ('config',)
    search_fields = ('config__instrument__symbol', 'config__data_source__name')
    date_hierarchy = 'start_time'
    readonly_fields = ('created_at', 'updated_at')