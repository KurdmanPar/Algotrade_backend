# apps/strategies/admin.py
from django.contrib import admin
from .models import Strategy, StrategyVersion, StrategyAssignment, BacktestRun, BacktestResult

@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'category', 'is_active', 'created_at')
    list_filter = ('category', 'is_active')
    raw_id_fields = ('owner',)

@admin.register(StrategyVersion)
class StrategyVersionAdmin(admin.ModelAdmin):
    list_display = ('strategy', 'version', 'is_approved_for_live', 'created_at')
    list_filter = ('is_approved_for_live',)
    raw_id_fields = ('strategy',)

@admin.register(StrategyAssignment)
class StrategyAssignmentAdmin(admin.ModelAdmin):
    list_display = ('strategy_version', 'bot', 'is_active', 'weight')
    list_filter = ('is_active',)
    raw_id_fields = ('strategy_version', 'bot')

@admin.register(BacktestRun)
class BacktestRunAdmin(admin.ModelAdmin):
    list_display = ('strategy_version', 'owner', 'status', 'instrument', 'start_datetime', 'end_datetime', 'initial_capital')
    list_filter = ('status', 'strategy_version')
    raw_id_fields = ('strategy_version', 'owner', 'instrument', 'exchange_account')

@admin.register(BacktestResult)
class BacktestResultAdmin(admin.ModelAdmin):
    list_display = ('backtest_run', 'order_id', 'trade_id', 'side', 'quantity', 'price', 'timestamp')
    list_filter = ('side', 'timestamp')
    raw_id_fields = ('backtest_run',) # حذف 'order' از اینجا