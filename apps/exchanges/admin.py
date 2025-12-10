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


class ExchangeAccountInline(admin.TabularInline):
    """
    Inline admin for ExchangeAccount within the User admin.
    """
    model = ExchangeAccount
    extra = 0
    fields = ('exchange', 'label', 'is_active', 'is_paper_trading', 'last_sync_at', 'link_to_details')
    readonly_fields = ('link_to_details',)

    def link_to_details(self, obj):
        if obj.pk:  # فقط اگر شیء ذخیره شده بود
            url = reverse('admin:exchanges_exchangeaccount_change', args=[obj.pk])
            return format_html('<a href="{}">View Details</a>', url)
        return "N/A"
    link_to_details.short_description = "Details"


class WalletInline(admin.TabularInline):
    """
    Inline admin for Wallet within the ExchangeAccount admin.
    """
    model = Wallet
    extra = 0
    fields = ('wallet_type', 'description', 'is_default', 'leverage')


class WalletBalanceInline(admin.TabularInline):
    """
    Inline admin for WalletBalance within the Wallet admin.
    """
    model = WalletBalance
    extra = 0
    fields = ('asset_symbol', 'total_balance', 'available_balance', 'in_order_balance')


class OrderHistoryInline(admin.TabularInline):
    """
    Inline admin for OrderHistory within the ExchangeAccount admin.
    """
    model = OrderHistory
    extra = 0
    fields = ('order_id', 'symbol', 'side', 'order_type', 'status', 'price', 'quantity', 'time_placed')
    readonly_fields = ('time_placed',) # معمولاً زمان خودکار ثبت می‌شود
    can_delete = False # تاریخچه سفارشات حذف نمی‌شوند


@admin.register(Exchange)
class ExchangeAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'type', 'is_active', 'is_sandbox', 'rate_limit_per_second')
    list_filter = ('type', 'is_active', 'is_sandbox')
    search_fields = ('name', 'code')
    readonly_fields = ('created_at', 'updated_at') # اگر از BaseModel ارث می‌برد
    fieldsets = (
        (None, {
            'fields': ('name', 'code', 'type', 'is_active')
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
            'fields': ('is_sandbox', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ExchangeAccount)
class ExchangeAccountAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'exchange', 'label', 'is_active', 'is_paper_trading', 'last_sync_at')
    list_filter = ('exchange', 'is_active', 'is_paper_trading')
    search_fields = ('user__email', 'label', 'exchange__name')
    raw_id_fields = ('user', 'exchange') # برای انتخاب کاربر و صرافی از طریق جستجو
    readonly_fields = ('created_at', 'updated_at', 'last_sync_at')
    inlines = [WalletInline, OrderHistoryInline] # نمایش والتس و سفارشات به صورت درون‌خطی

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'
    user_email.admin_order_field = 'user__email' # امکان مرتب‌سازی

    fieldsets = (
        (None, {
            'fields': ('user', 'exchange', 'label', 'is_active', 'is_paper_trading')
        }),
        ('Security & Credentials', {
            'fields': ('encrypted_key_iv', 'extra_credentials'), # فقط IV و اطلاعات اضافی، نه کلیدها
            'classes': ('collapse',)
        }),
        ('Account Info (Read Only)', {
            'fields': ('account_info', 'trading_permissions'),
            'classes': ('collapse',)
        }),
        ('Meta', {
            'fields': ('last_login_ip', 'created_ip', 'last_sync_at', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('exchange_account_label', 'wallet_type', 'description', 'is_default', 'leverage')
    list_filter = ('wallet_type', 'is_default')
    search_fields = ('exchange_account__label', 'exchange_account__user__email', 'description')
    raw_id_fields = ('exchange_account',)
    inlines = [WalletBalanceInline]

    def exchange_account_label(self, obj):
        return obj.exchange_account.label or "No Label"
    exchange_account_label.short_description = 'Account Label'
    exchange_account_label.admin_order_field = 'exchange_account__label'


@admin.register(WalletBalance)
class WalletBalanceAdmin(admin.ModelAdmin):
    list_display = ('wallet_repr', 'asset_symbol', 'total_balance', 'available_balance', 'updated_at')
    list_filter = ('asset_symbol', 'wallet__exchange_account__exchange') # فیلتر بر اساس صرافی
    search_fields = ('wallet__exchange_account__label', 'asset_symbol')
    raw_id_fields = ('wallet',)
    list_per_page = 20 # تعداد رکوردها در هر صفحه

    def wallet_repr(self, obj):
        return f"{obj.wallet.exchange_account.label} - {obj.wallet.wallet_type}"
    wallet_repr.short_description = 'Wallet (Account - Type)'


@admin.register(AggregatedPortfolio)
class AggregatedPortfolioAdmin(admin.ModelAdmin):
    list_display = ('user_email', 'base_currency', 'total_equity', 'total_unrealized_pnl', 'updated_at')
    search_fields = ('user__email',)
    raw_id_fields = ('user',)
    readonly_fields = ('created_at', 'updated_at')

    def user_email(self, obj):
        return obj.user.email
    user_email.short_description = 'User Email'


@admin.register(AggregatedAssetPosition)
class AggregatedAssetPositionAdmin(admin.ModelAdmin):
    list_display = ('aggregated_portfolio_user', 'asset_symbol', 'total_quantity', 'total_value_in_base_currency')
    list_filter = ('asset_symbol',)
    search_fields = ('aggregated_portfolio__user__email', 'asset_symbol')
    raw_id_fields = ('aggregated_portfolio',)

    def aggregated_portfolio_user(self, obj):
        return obj.aggregated_portfolio.user.email
    aggregated_portfolio_user.short_description = 'Portfolio User'


@admin.register(OrderHistory)
class OrderHistoryAdmin(admin.ModelAdmin):
    list_display = ('exchange_account_label', 'order_id', 'symbol', 'side', 'order_type', 'status', 'price', 'quantity', 'time_placed')
    list_filter = ('status', 'side', 'order_type', 'exchange_account__exchange', 'time_placed')
    search_fields = ('order_id', 'symbol', 'exchange_account__label', 'exchange_account__user__email')
    raw_id_fields = ('exchange_account', 'trading_bot') # اگر trading_bot وجود داشته باشد
    readonly_fields = ('time_placed', 'time_updated')
    date_hierarchy = 'time_placed' # امکان مرتب‌سازی بر اساس تاریخ

    def exchange_account_label(self, obj):
        return obj.exchange_account.label or "No Label"
    exchange_account_label.short_description = 'Account Label'


@admin.register(MarketDataCandle)
class MarketDataCandleAdmin(admin.ModelAdmin):
    list_display = ('exchange', 'symbol', 'interval', 'open_time', 'open', 'high', 'low', 'close')
    list_filter = ('exchange', 'symbol', 'interval', 'open_time')
    search_fields = ('symbol', 'exchange__name')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'open_time'
    list_per_page = 50

    # ممکن است بخواهید فیلدهایی مانند 'number_of_trades' را نیز در list_display اضافه کنید
