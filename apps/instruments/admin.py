# apps/instruments/admin.py
from django.contrib import admin
from .models import (
    InstrumentGroup, InstrumentCategory, Instrument, InstrumentExchangeMap,
    IndicatorGroup, Indicator, IndicatorParameter, IndicatorTemplate,
    PriceActionPattern, SmartMoneyConcept, AIMetric
)

@admin.register(InstrumentGroup)
class InstrumentGroupAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(InstrumentCategory)
class InstrumentCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Instrument)
class InstrumentAdmin(admin.ModelAdmin):
    list_display = ('symbol', 'name', 'group', 'category', 'base_asset', 'quote_asset', 'is_active')
    list_filter = ('group', 'category', 'is_active')
    search_fields = ('symbol', 'name')

@admin.register(InstrumentExchangeMap)
class InstrumentExchangeMapAdmin(admin.ModelAdmin):
    list_display = ('exchange', 'exchange_symbol', 'instrument', 'is_active')
    list_filter = ('exchange', 'is_active')
    raw_id_fields = ('exchange', 'instrument')

@admin.register(IndicatorGroup)
class IndicatorGroupAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'group', 'is_active', 'is_builtin')
    list_filter = ('group', 'is_active', 'is_builtin')
    search_fields = ('name', 'code')

@admin.register(IndicatorParameter)
class IndicatorParameterAdmin(admin.ModelAdmin):
    list_display = ('indicator', 'name', 'data_type')
    raw_id_fields = ('indicator',)

@admin.register(IndicatorTemplate)
class IndicatorTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'indicator', 'is_active')
    list_filter = ('is_active',)
    raw_id_fields = ('indicator',)

@admin.register(PriceActionPattern)
class PriceActionPatternAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    list_filter = ('is_active',)

@admin.register(SmartMoneyConcept)
class SmartMoneyConceptAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_active')
    list_filter = ('is_active',)

@admin.register(AIMetric)
class AIMetricAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'data_type', 'is_active')
    list_filter = ('data_type', 'is_active',)
