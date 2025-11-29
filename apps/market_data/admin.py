# apps/market_data/admin.py
from django.contrib import admin
from .models import DataSource, MarketDataConfig, MarketDataSyncLog, MarketDataSnapshot

@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'is_active')
    list_filter = ('type', 'is_active')

@admin.register(MarketDataConfig)
class MarketDataConfigAdmin(admin.ModelAdmin):
    list_display = ('instrument', 'timeframe', 'data_source', 'storage_backend', 'is_active')
    list_filter = ('storage_backend', 'is_active', 'is_realtime')
    raw_id_fields = ('instrument', 'data_source')

@admin.register(MarketDataSyncLog)
class MarketDataSyncLogAdmin(admin.ModelAdmin):
    list_display = ('config', 'status', 'start_time', 'end_time', 'records_synced')
    list_filter = ('status', 'start_time')
    raw_id_fields = ('config',)

@admin.register(MarketDataSnapshot)
class MarketDataSnapshotAdmin(admin.ModelAdmin):
    list_display = ('instrument', 'timeframe', 'timestamp', 'close_price')
    list_filter = ('timeframe', 'timestamp')
    raw_id_fields = ('instrument',)
