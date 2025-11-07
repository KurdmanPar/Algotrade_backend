from django.contrib import admin
from .models import User, Role, UserRole, Strategy, Indicator, StrategyIndicator, Backtest, Bot, Trade, Signal

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'is_staff', 'is_active')
    search_fields = ('username', 'email')

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')

@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ('user', 'role')

@admin.register(Strategy)
class StrategyAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'type', 'is_active', 'created_at')
    search_fields = ('name', 'owner__username')

@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)

@admin.register(StrategyIndicator)
class StrategyIndicatorAdmin(admin.ModelAdmin):
    list_display = ('strategy', 'indicator')

@admin.register(Backtest)
class BacktestAdmin(admin.ModelAdmin):
    list_display = ('strategy', 'status', 'start_time', 'end_time')
    list_filter = ('status',)

@admin.register(Bot)
class BotAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'strategy', 'symbol', 'exchange', 'is_active')
    search_fields = ('name', 'user__username', 'symbol')

@admin.register(Trade)
class TradeAdmin(admin.ModelAdmin):
    list_display = ('bot', 'symbol', 'status', 'entry_price', 'exit_price', 'profit_loss', 'timestamp')
    list_filter = ('status',)

@admin.register(Signal)
class SignalAdmin(admin.ModelAdmin):
    list_display = ('strategy', 'symbol', 'signal_type', 'confidence', 'processed', 'timestamp')
    list_filter = ('signal_type', 'processed')

# Register your models here.
