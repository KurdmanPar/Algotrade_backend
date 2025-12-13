# apps/exchanges/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    Exchange,
    ExchangeAccount,
    Wallet,
    WalletBalance,
    AggregatedPortfolio,
    AggregatedAssetPosition,
    OrderHistory,
    MarketDataCandle,
)
from apps.accounts.models import CustomUser # import مدل کاربر
from apps.bots.models import TradingBot # import مدل بات (اگر وجود داشت)
from apps.instruments.models import Instrument # import مدل نماد (اگر وجود داشت)
from apps.core.models import AuditLog # import مدل حسابرسی (اگر وجود داشت)

# --- مدیریت مدل Exchange ---
@admin.register(Exchange)
class ExchangeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'type', 'is_active', 'is_sandbox', 'rate_limit_per_second', 'created_at', 'updated_at')
    list_filter = ('type', 'is_active', 'is_sandbox', 'created_at', 'updated_at')
    search_fields = ('name', 'code')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'code', 'type', 'is_active', 'is_sandbox')
        }),
        ('API Information', {
            'fields': ('base_url', 'ws_url', 'api_docs_url'),
            'classes': ('collapse',) # قابل جمع شدن
        }),
        ('Limits', {
            'fields': ('rate_limit_per_second', 'fees_structure', 'limits'),
            'classes': ('collapse',)
        }),
        ('Meta', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

# --- مدیریت مدل ExchangeAccount ---
class LinkedBotsInline(admin.TabularInline):
    """
    Inline admin for managing linked bots within the ExchangeAccount admin.
    """
    model = ExchangeAccount.linked_bots.through # M2M relation
    extra = 0
    raw_id_fields = ('tradingbot',) # برای انتخاب کارآمد

@admin.register(ExchangeAccount)
class ExchangeAccountAdmin(admin.ModelAdmin):
    list_display = ('owner_email_link', 'exchange_name', 'label', 'is_active', 'is_paper_trading', 'last_sync_at', 'created_at', 'updated_at')
    list_filter = ('exchange', 'is_active', 'is_paper_trading', 'last_sync_at', 'created_at', 'owner')
    search_fields = ('owner__email', 'label', 'exchange__name', 'exchange_symbol')
    readonly_fields = ('owner', 'created_at', 'updated_at', 'last_sync_at', '_api_key_encrypted', '_api_secret_encrypted', 'encrypted_key_iv') # کلیدهای رمزنگاری شده فقط خواندنی
    raw_id_fields = ('owner', 'exchange') # برای انتخاب کارآمد
    inlines = [LinkedBotsInline] # اضافه کردن inline مدیریت بات‌ها
    fieldsets = (
        (None, {
            'fields': ('owner', 'exchange', 'label', 'is_active', 'is_paper_trading')
        }),
        ('Security & Credentials', {
            'fields': ('_api_key_encrypted', '_api_secret_encrypted', 'encrypted_key_iv', 'extra_credentials'),
            'classes': ('collapse',)
        }),
        ('Account Info', {
            'fields': ('account_info', 'trading_permissions'),
            'classes': ('collapse',)
        }),
        ('Security', {
            'fields': ('last_login_ip', 'created_ip'),
        }),
        ('Meta', {
            'fields': ('created_at', 'updated_at', 'last_sync_at'),
            'classes': ('collapse',)
        }),
    )

    def owner_email_link(self, obj):
        """
        Creates a link to the owner's admin page.
        """
        if obj.owner:
            url = reverse("admin:accounts_customuser_change", args=[obj.owner.id]) # فرض: اپلیکیشن accounts، مدل CustomUser
            return format_html('<a href="{}">{}</a>', url, obj.owner.email)
        return "-"
    owner_email_link.short_description = 'Owner Email'
    owner_email_link.admin_order_field = 'owner__email'

    def exchange_name(self, obj):
        """
        Displays the exchange name.
        """
        return obj.exchange.name
    exchange_name.short_description = 'Exchange'
    exchange_name.admin_order_field = 'exchange__name'

# --- مدیریت مدل Wallet ---
@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('exchange_account_owner_email', 'exchange_account_label', 'wallet_type', 'is_default', 'is_margin_enabled', 'leverage', 'created_at', 'updated_at')
    list_filter = ('wallet_type', 'is_default', 'is_margin_enabled', 'exchange_account__exchange', 'created_at', 'exchange_account__owner')
    search_fields = ('exchange_account__label', 'exchange_account__owner__email', 'wallet_type')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('exchange_account',)

    def exchange_account_owner_email(self, obj):
        """
        Displays the owner's email of the related exchange account.
        """
        return obj.exchange_account.owner.email
    exchange_account_owner_email.short_description = 'Account Owner'
    exchange_account_owner_email.admin_order_field = 'exchange_account__owner__email'

    def exchange_account_label(self, obj):
        """
        Displays the label of the related exchange account.
        """
        return obj.exchange_account.label
    exchange_account_label.short_description = 'Account Label'
    exchange_account_label.admin_order_field = 'exchange_account__label'

# --- مدیریت مدل WalletBalance ---
@admin.register(WalletBalance)
class WalletBalanceAdmin(admin.ModelAdmin):
    list_display = ('wallet_repr', 'asset_symbol', 'total_balance', 'available_balance', 'in_order_balance', 'frozen_balance', 'created_at', 'updated_at')
    list_filter = ('asset_symbol', 'wallet__exchange_account__exchange', 'created_at', 'updated_at')
    search_fields = ('wallet__exchange_account__label', 'asset_symbol', 'wallet__exchange_account__owner__email')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('wallet',)
    ordering = ['-created_at']

    def wallet_repr(self, obj):
        """
        Displays a summary of the wallet.
        """
        return f"{obj.wallet.exchange_account.label} - {obj.wallet.wallet_type}"
    wallet_repr.short_description = 'Wallet (Account - Type)'

# --- مدیریت مدل AggregatedPortfolio ---
@admin.register(AggregatedPortfolio)
class AggregatedPortfolioAdmin(admin.ModelAdmin):
    list_display = ('owner_email_link', 'base_currency', 'total_equity', 'total_unrealized_pnl', 'total_pnl_percentage', 'last_valuation_at', 'created_at', 'updated_at')
    list_filter = ('base_currency', 'last_valuation_at', 'created_at', 'owner')
    search_fields = ('owner__email',)
    readonly_fields = ('owner', 'created_at', 'updated_at')
    raw_id_fields = ('owner',)

    def owner_email_link(self, obj):
        """
        Creates a link to the owner's admin page.
        """
        if obj.owner:
            url = reverse("admin:accounts_customuser_change", args=[obj.owner.id])
            return format_html('<a href="{}">{}</a>', url, obj.owner.email)
        return "-"
    owner_email_link.short_description = 'Owner Email'
    owner_email_link.admin_order_field = 'owner__email'

# --- مدیریت مدل AggregatedAssetPosition ---
@admin.register(AggregatedAssetPosition)
class AggregatedAssetPositionAdmin(admin.ModelAdmin):
    list_display = ('portfolio_owner_email', 'asset_symbol', 'total_quantity', 'total_value_in_base_currency', 'created_at', 'updated_at')
    list_filter = ('asset_symbol', 'aggregated_portfolio__base_currency', 'created_at', 'updated_at', 'aggregated_portfolio__owner')
    search_fields = ('aggregated_portfolio__owner__email', 'asset_symbol')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('aggregated_portfolio',)

    def portfolio_owner_email(self, obj):
        """
        Displays the owner's email of the related aggregated portfolio.
        """
        return obj.aggregated_portfolio.owner.email
    portfolio_owner_email.short_description = 'Portfolio Owner'
    portfolio_owner_email.admin_order_field = 'aggregated_portfolio__owner__email'

# --- مدیریت مدل OrderHistory ---
@admin.register(OrderHistory)
class OrderHistoryAdmin(admin.ModelAdmin):
    list_display = ('exchange_account_owner_email', 'exchange_account_label', 'order_id', 'symbol', 'side', 'order_type', 'status', 'price', 'quantity', 'time_placed', 'time_updated')
    list_filter = ('status', 'side', 'order_type', 'symbol', 'time_placed', 'time_updated', 'exchange_account__exchange', 'exchange_account__owner')
    search_fields = ('order_id', 'symbol', 'exchange_account__label', 'exchange_account__owner__email')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('exchange_account', 'trading_bot')
    date_hierarchy = 'time_placed'
    ordering = ['-time_placed']

    def exchange_account_owner_email(self, obj):
        return obj.exchange_account.owner.email
    exchange_account_owner_email.short_description = 'Account Owner'
    exchange_account_owner_email.admin_order_field = 'exchange_account__owner__email'

    def exchange_account_label(self, obj):
        return obj.exchange_account.label
    exchange_account_label.short_description = 'Account Label'
    exchange_account_label.admin_order_field = 'exchange_account__label'

# --- مدیریت مدل MarketDataCandle ---
@admin.register(MarketDataCandle)
class MarketDataCandleAdmin(admin.ModelAdmin):
    list_display = ('exchange_name', 'symbol', 'interval', 'open_time', 'open', 'high', 'low', 'close', 'volume')
    list_filter = ('exchange', 'symbol', 'interval', 'open_time', 'created_at')
    search_fields = ('symbol', 'exchange__name')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('exchange',)
    date_hierarchy = 'open_time'
    ordering = ['-open_time']
    list_per_page = 50 # تعداد نمایش در هر صفحه

    def exchange_name(self, obj):
        return obj.exchange.name
    exchange_name.short_description = 'Exchange'
    exchange_name.admin_order_field = 'exchange__name'

# --- سایر مدیریت‌های مدل (اگر وجود داشتند) ---
# می‌توانید برای سایر مدل‌هایی که در exchanges/models.py تعریف می‌کنید نیز ModelAdmin بنویسید
# مثلاً اگر مدل ExchangeConnectionLog وجود داشت:
# @admin.register(ExchangeConnectionLog)
# class ExchangeConnectionLogAdmin(admin.ModelAdmin):
#     list_display = ('exchange_account', 'status', 'reason', 'connected_at', 'disconnected_at')
#     list_filter = ('status', 'connected_at', 'disconnected_at')
#     search_fields = ('exchange_account__label', 'reason')
#     readonly_fields = ('connected_at', 'disconnected_at')
#     raw_id_fields = ('exchange_account',)

logger.info("Exchanges admin interfaces loaded successfully.")
