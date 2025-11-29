# apps/exchanges/admin.py
from django.contrib import admin
from .models import Exchange, ExchangeAccount, Wallet, WalletBalance, AggregatedPortfolio, AggregatedAssetPosition

@admin.register(Exchange)
class ExchangeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'type', 'is_active')
    search_fields = ('name', 'code')
    list_filter = ('type', 'is_active')

@admin.register(ExchangeAccount)
class ExchangeAccountAdmin(admin.ModelAdmin):
    list_display = ('user', 'exchange', 'label', 'is_active', 'last_sync_at')
    list_filter = ('exchange', 'is_active')
    raw_id_fields = ('user', 'exchange')

@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('exchange_account', 'wallet_type', 'is_default', 'leverage')
    list_filter = ('wallet_type', 'is_default')
    raw_id_fields = ('exchange_account',)

@admin.register(WalletBalance)
class WalletBalanceAdmin(admin.ModelAdmin):
    list_display = ('wallet', 'asset_symbol', 'total_balance', 'available_balance', 'updated_at')
    list_filter = ('asset_symbol',)
    raw_id_fields = ('wallet',)

@admin.register(AggregatedPortfolio)
class AggregatedPortfolioAdmin(admin.ModelAdmin):
    list_display = ('user', 'base_currency', 'total_equity', 'total_unrealized_pnl', 'updated_at')
    raw_id_fields = ('user',)

@admin.register(AggregatedAssetPosition)
class AggregatedAssetPositionAdmin(admin.ModelAdmin):
    list_display = ('aggregated_portfolio', 'asset_symbol', 'total_quantity', 'total_value_in_base_currency')
    raw_id_fields = ('aggregated_portfolio',)