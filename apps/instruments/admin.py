# apps/instruments/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    InstrumentGroup,
    InstrumentCategory,
    Instrument,
    InstrumentExchangeMap,
    IndicatorGroup,
    Indicator,
    IndicatorParameter,
    IndicatorTemplate,
    PriceActionPattern,
    SmartMoneyConcept,
    AIMetric,
    InstrumentWatchlist,
)

class InstrumentGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')

admin.site.register(InstrumentGroup, InstrumentGroupAdmin)


class InstrumentCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'supports_leverage', 'supports_shorting', 'created_at', 'updated_at')
    list_filter = ('supports_leverage', 'supports_shorting')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')

admin.site.register(InstrumentCategory, InstrumentCategoryAdmin)


class InstrumentExchangeMapInline(admin.TabularInline):
    """
    Inline admin for InstrumentExchangeMap within the Instrument admin.
    Allows managing exchange-specific details directly from the instrument page.
    """
    model = InstrumentExchangeMap
    extra = 0
    fields = (
        'exchange_link', 'exchange_symbol', 'tick_size', 'lot_size',
        'min_notional', 'max_notional', 'is_active', 'created_at'
    )
    readonly_fields = ('exchange_link', 'created_at')

    def exchange_link(self, obj):
        if obj.exchange_id: # اطمینان از وجود ID
            url = reverse("admin:exchanges_exchange_change", args=[obj.exchange_id]) # فرض: اپلیکیشن 'exchanges' وجود دارد
            return format_html('<a href="{}">{}</a>', url, obj.exchange.name)
        return "-" # یا obj.exchange.name اگر obj وجود نداشته باشد
    exchange_link.short_description = "Exchange"


class InstrumentAdmin(admin.ModelAdmin):
    list_display = (
        'symbol', 'name', 'group_name', 'category_name', 'base_asset', 'quote_asset',
        'tick_size', 'lot_size', 'is_active', 'created_at'
    )
    list_filter = ('group', 'category', 'is_active', 'created_at')
    search_fields = ('symbol', 'name', 'base_asset', 'quote_asset')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [InstrumentExchangeMapInline] # نمایش ارتباط با صرافی‌ها
    fieldsets = (
        (None, {
            'fields': ('symbol', 'name', 'group', 'category')
        }),
        ('Assets', {
            'fields': ('base_asset', 'quote_asset'),
        }),
        ('Precision & Limits (Default)', {
            'fields': ('tick_size', 'lot_size'),
            'classes': ('collapse',) # قابل جمع شدن
        }),
        ('Status', {
            'fields': ('is_active',),
        }),
        ('Dates', {
            'fields': ('launch_date', 'delisting_date'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Meta', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def group_name(self, obj):
        return obj.group.name
    group_name.short_description = 'Group'
    group_name.admin_order_field = 'group__name' # امکان مرتب‌سازی

    def category_name(self, obj):
        return obj.category.name if obj.category else "-" # در صورت NULL
    category_name.short_description = 'Category'
    category_name.admin_order_field = 'category__name'

admin.site.register(Instrument, InstrumentAdmin)


class InstrumentExchangeMapAdmin(admin.ModelAdmin):
    list_display = (
        'exchange_name', 'instrument_symbol', 'exchange_symbol',
        'tick_size', 'lot_size', 'is_active', 'created_at'
    )
    list_filter = ('exchange', 'instrument', 'is_active', 'created_at')
    search_fields = ('exchange__name', 'exchange_symbol', 'instrument__symbol')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('exchange', 'instrument') # برای انتخاب کارآمد از طریق جستجو
    fieldsets = (
        (None, {
            'fields': ('exchange', 'instrument', 'exchange_symbol')
        }),
        ('Exchange-Specific Precision & Limits', {
            'fields': (
                'tick_size', 'lot_size', 'min_notional', 'max_notional',
                'min_lot_size', 'max_lot_size'
            ),
        }),
        ('Margin & Leverage', {
            'fields': ('max_leverage', 'initial_margin_ratio', 'maintenance_margin_ratio'),
            'classes': ('collapse',)
        }),
        ('Status & Dates', {
            'fields': ('is_active', 'is_margin_enabled', 'is_funding_enabled', 'listing_date', 'delisting_date'),
        }),
        ('Meta', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def exchange_name(self, obj):
        return obj.exchange.name
    exchange_name.short_description = 'Exchange'
    exchange_name.admin_order_field = 'exchange__name'

    def instrument_symbol(self, obj):
        return obj.instrument.symbol
    instrument_symbol.short_description = 'Instrument Symbol'
    instrument_symbol.admin_order_field = 'instrument__symbol'

admin.site.register(InstrumentExchangeMap, InstrumentExchangeMapAdmin)


class IndicatorGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')

admin.site.register(IndicatorGroup, IndicatorGroupAdmin)


class IndicatorParameterInline(admin.TabularInline):
    """
    Inline admin for IndicatorParameter within the Indicator admin.
    """
    model = IndicatorParameter
    extra = 1 # یک فیلد خالی اضافه می‌کند
    fields = ('name', 'display_name', 'data_type', 'default_value', 'min_value', 'max_value', 'choices')


class IndicatorAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'group_name', 'is_active', 'is_builtin', 'version', 'created_at')
    list_filter = ('group', 'is_active', 'is_builtin', 'created_at')
    search_fields = ('name', 'code')
    readonly_fields = ('created_at', 'updated_at', 'version')
    inlines = [IndicatorParameterInline] # نمایش پارامترهای اندیکاتور
    fieldsets = (
        (None, {
            'fields': ('name', 'code', 'group', 'description')
        }),
        ('Status & Type', {
            'fields': ('is_active', 'is_builtin'),
        }),
        ('Calculation & Data', {
            'fields': ('calculation_frequency', 'requires_price_data', 'output_types'),
            'classes': ('collapse',)
        }),
        ('Meta', {
            'fields': ('version', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def group_name(self, obj):
        return obj.group.name
    group_name.short_description = 'Group'
    group_name.admin_order_field = 'group__name'

admin.site.register(Indicator, IndicatorAdmin)


class IndicatorTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'indicator_name', 'is_active', 'created_at', 'updated_at')
    list_filter = ('indicator', 'is_active', 'created_at')
    search_fields = ('name', 'indicator__name')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('indicator',) # برای انتخاب کارآمد
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'indicator', 'is_active')
        }),
        ('Parameters (JSON)', {
            'fields': ('parameters',), # ممکن است نیاز به یک ویجت خاص برای JSON داشته باشد
        }),
        ('Meta', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def indicator_name(self, obj):
        return obj.indicator.name
    indicator_name.short_description = 'Indicator'
    indicator_name.admin_order_field = 'indicator__name'

admin.site.register(IndicatorTemplate, IndicatorTemplateAdmin)


class PriceActionPatternAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'code')
    readonly_fields = ('created_at', 'updated_at')

admin.site.register(PriceActionPattern, PriceActionPatternAdmin)


class SmartMoneyConceptAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'code')
    readonly_fields = ('created_at', 'updated_at')

admin.site.register(SmartMoneyConcept, SmartMoneyConceptAdmin)


class AIMetricAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'data_type', 'is_active', 'created_at', 'updated_at')
    list_filter = ('data_type', 'is_active', 'created_at')
    search_fields = ('name', 'code')
    readonly_fields = ('created_at', 'updated_at')

admin.site.register(AIMetric, AIMetricAdmin)


class InstrumentWatchlistAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner_username', 'is_public', 'created_at', 'updated_at')
    list_filter = ('is_public', 'created_at', 'owner')
    search_fields = ('name', 'owner__username', 'instruments__symbol')
    readonly_fields = ('created_at', 'updated_at')
    raw_id_fields = ('owner', 'instruments') # برای انتخاب کارآمد
    filter_horizontal = ('instruments',) # ویجتی برای انتخاب چندتایی
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'owner', 'is_public')
        }),
        ('Instruments', {
            'fields': ('instruments',), # با استفاده از filter_horizontal
        }),
        ('Meta', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def owner_username(self, obj):
        return obj.owner.username
    owner_username.short_description = 'Owner'
    owner_username.admin_order_field = 'owner__username'

admin.site.register(InstrumentWatchlist, InstrumentWatchlistAdmin)
