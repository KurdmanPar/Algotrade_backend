# apps/strategies/admin.py
from django.contrib import admin
from .models import Strategy, StrategyVersion, StrategyAssignment

@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'category', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'created_at')
    raw_id_fields = ('owner',)
    search_fields = ('name', 'owner__email')

@admin.register(StrategyVersion)
class StrategyVersionAdmin(admin.ModelAdmin):
    list_display = ('strategy', 'version', 'is_approved_for_live', 'created_at')
    list_filter = ('is_approved_for_live', 'created_at')
    raw_id_fields = ('strategy',)
    search_fields = ('version', 'strategy__name')

@admin.register(StrategyAssignment)
class StrategyAssignmentAdmin(admin.ModelAdmin):
    list_display = ('strategy_version', 'bot', 'is_active', 'weight', 'priority')
    list_filter = ('is_active', 'priority')
    raw_id_fields = ('strategy_version', 'bot')
    search_fields = ('strategy_version__strategy__name', 'bot__name')