# apps/backtesting/admin.py
from django.contrib import admin
from .models import BacktestRun, BacktestResult

@admin.register(BacktestRun)
class BacktestRunAdmin(admin.ModelAdmin):
    list_display = ('strategy_version', 'owner', 'status', 'instrument', 'start_datetime', 'end_datetime', 'initial_capital', 'created_at')
    list_filter = ('status', 'strategy_version', 'created_at')
    raw_id_fields = ('strategy_version', 'owner', 'instrument', 'exchange_account')
    search_fields = ('strategy_version__strategy__name', 'owner__email')

@admin.register(BacktestResult)
class BacktestResultAdmin(admin.ModelAdmin):
    list_display = ('backtest_run', 'order_id', 'trade_id', 'side', 'quantity', 'price', 'timestamp')
    list_filter = ('side', 'timestamp')
    raw_id_fields = ('backtest_run',)
    search_fields = ('order_id', 'trade_id')
