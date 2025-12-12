# apps/core/filters.py

import django_filters
from django.db import models
from .models import (
    BaseModel,
    BaseOwnedModel,
    AuditLog,
    SystemSetting,
    CacheEntry,
    # سایر مدل‌های شما
)

# --- فیلترهای پایه ---

class BaseFilterSet(django_filters.FilterSet):
    """
    FilterSet پایه شامل فیلترهای عمومی برای مدل‌هایی که از BaseModel ارث می‌برند.
    """
    created_after = django_filters.DateTimeFilter(field_name="created_at", lookup_expr='gte')
    created_before = django_filters.DateTimeFilter(field_name="created_at", lookup_expr='lte')
    updated_after = django_filters.DateTimeFilter(field_name="updated_at", lookup_expr='gte')
    updated_before = django_filters.DateTimeFilter(field_name="updated_at", lookup_expr='lte')

    class Meta:
        model = BaseModel # مدل پایه، فقط برای نمایش فیلدهای عمومی
        fields = {
            'id': ['exact', 'in'], # فیلتر بر اساس ID
            'created_at': ['exact', 'range', 'year', 'month', 'day'], # مثال فیلترهای تاریخ
            'updated_at': ['exact', 'range', 'year', 'month', 'day'],
        }
        abstract = True # این FilterSet انتزاعی است


class OwnedFilterSet(BaseFilterSet):
    """
    FilterSet پایه برای مدل‌هایی که از BaseOwnedModel ارث می‌برند.
    امکان فیلتر کردن بر اساس owner.
    """
    owner = django_filters.NumberFilter(field_name="owner__id") # فرض: owner یک ForeignKey است
    owner_email = django_filters.CharFilter(field_name="owner__email", lookup_expr='iexact')

    class Meta(BaseFilterSet.Meta):
        model = BaseOwnedModel # مدل پایه مالک‌دار
        fields = BaseFilterSet.Meta.fields.copy()
        fields.update({
            'owner': ['exact'],
            'owner__email': ['iexact', 'icontains'],
        })
        abstract = True


# --- فیلترهای خاص برای مدل‌های Core ---

class AuditLogFilterSet(BaseFilterSet):
    """
    FilterSet for the AuditLog model.
    """
    user = django_filters.NumberFilter(field_name="user__id")
    user_email = django_filters.CharFilter(field_name="user__email", lookup_expr='icontains')
    action = django_filters.CharFilter(lookup_expr='iexact')
    target_model = django_filters.CharFilter(lookup_expr='iexact')
    target_id = django_filters.UUIDFilter() # فرض: target_id یک UUID است
    ip_address = django_filters.CharFilter(lookup_expr='iexact')

    class Meta(BaseFilterSet.Meta):
        model = AuditLog
        fields = BaseFilterSet.Meta.fields.copy()
        fields.update({
            'user': ['exact'],
            'user__email': ['icontains'],
            'action': ['iexact'],
            'target_model': ['iexact'],
            'target_id': ['exact'],
            'ip_address': ['iexact'],
        })


class SystemSettingFilterSet(BaseFilterSet):
    """
    FilterSet for the SystemSetting model.
    """
    key = django_filters.CharFilter(lookup_expr='iexact')
    is_sensitive = django_filters.BooleanFilter()
    is_active = django_filters.BooleanFilter()
    data_type = django_filters.CharFilter(lookup_expr='iexact')

    class Meta(BaseFilterSet.Meta):
        model = SystemSetting
        fields = BaseFilterSet.Meta.fields.copy()
        fields.update({
            'key': ['iexact', 'icontains'],
            'is_sensitive': ['exact'],
            'is_active': ['exact'],
            'data_type': ['iexact'],
        })


class CacheEntryFilterSet(BaseFilterSet):
    """
    FilterSet for the CacheEntry model.
    """
    key = django_filters.CharFilter(lookup_expr='icontains')
    expires_after = django_filters.DateTimeFilter(field_name="expires_at", lookup_expr='gte')
    expires_before = django_filters.DateTimeFilter(field_name="expires_at", lookup_expr='lte')

    class Meta(BaseFilterSet.Meta):
        model = CacheEntry
        fields = BaseFilterSet.Meta.fields.copy()
        fields.update({
            'key': ['icontains'],
            'expires_at': ['exact', 'range', 'gte', 'lte'],
        })

# --- مثال: فیلتر برای یک مدل نماد ---
# اگر مدل Instrument در این اپلیکیشن بود یا از Core ارث می‌برد:
# class InstrumentFilterSet(OwnedFilterSet): # اگر Instrument از BaseOwnedModel ارث ببرد
#     symbol = django_filters.CharFilter(lookup_expr='iexact')
#     base_asset = django_filters.CharFilter(lookup_expr='iexact')
#     quote_asset = django_filters.CharFilter(lookup_expr='iexact')
#     is_active = django_filters.BooleanFilter()
#
#     class Meta(OwnedFilterSet.Meta):
#         model = Instrument
#         fields = OwnedFilterSet.Meta.fields.copy()
#         fields.update({
#             'symbol': ['iexact', 'icontains'],
#             'base_asset': ['iexact'],
#             'quote_asset': ['iexact'],
#             'is_active': ['exact'],
#         })
