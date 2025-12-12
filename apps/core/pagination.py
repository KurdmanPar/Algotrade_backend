# apps/core/pagination.py

from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination
from rest_framework.response import Response
from django.core.paginator import Paginator as DjangoPaginator
from django.utils.functional import cached_property
import math

class CorePageNumberPagination(PageNumberPagination):
    """
    Standard page number pagination for API responses.
    Allows client to specify page size within limits.
    """
    page_size = 20  # تعداد آیتم در هر صفحه
    page_size_query_param = 'page_size'
    max_page_size = 100  # حداکثر تعداد آیتم در هر صفحه

    def get_paginated_response(self, data):
        """
        Customizes the paginated response format.
        """
        return Response({
            'links': {
                'next': self.get_next_link(),
                'previous': self.get_previous_link()
            },
            'count': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'current_page': self.page.number,
            'page_size': self.get_page_size(self.request),
            'results': data
        })

class CoreLimitOffsetPagination(LimitOffsetPagination):
    """
    Limit/offset pagination for API responses.
    Useful for scrolling through large datasets.
    """
    default_limit = 50
    limit_query_param = 'limit'
    offset_query_param = 'offset'
    max_limit = 200 # حداکثر تعداد آیتم قابل گرفتن در یک درخواست

    def get_paginated_response(self, data):
        """
        Customizes the limit/offset paginated response format.
        """
        return Response({
            'next_offset': self.offset + self.limit if self.offset + self.limit < self.count else None,
            'previous_offset': self.offset - self.limit if self.offset - self.limit >= 0 else None,
            'count': self.count,
            'limit': self.limit,
            'offset': self.offset,
            'results': data
        })

# --- مثال: یک کلاس صفحه‌بندی سفارشی برای داده‌های سری زمانی (مثل OHLCV) ---
class TimeBasedPagination(LimitOffsetPagination):
    """
    Pagination based on a timestamp field for time-series data.
    Allows requesting data for a specific time range with a limit.
    This is more suitable for market data where order matters significantly.
    """
    # این دو فیلد باید در نماها ارائه شوند
    timestamp_field = 'timestamp' # نام فیلد تایم‌استمپ در مدل
    default_limit = 1000
    max_limit = 5000

    def paginate_queryset(self, queryset, request, view=None):
        """
        Applies filtering based on start_time and end_time before pagination.
        """
        self.start_time = request.query_params.get('start_time', None)
        self.end_time = request.query_params.get('end_time', None)

        if self.start_time:
            try:
                start_dt = timezone.datetime.fromisoformat(self.start_time.replace('Z', '+00:00'))
                queryset = queryset.filter(**{f"{self.timestamp_field}__gte": start_dt})
            except ValueError:
                pass # یا خطای اعتبارسنجی ایجاد کنید

        if self.end_time:
            try:
                end_dt = timezone.datetime.fromisoformat(self.end_time.replace('Z', '+00:00'))
                queryset = queryset.filter(**{f"{self.timestamp_field}__lte": end_dt})
            except ValueError:
                pass # یا خطای اعتبارسنجی ایجاد کنید

        # مرتب‌سازی بر اساس زمان (جدیدترین آخر یا اول بسته به نیاز)
        # معمولاً برای داده‌های سری زمانی از قدیمی به جدید مرتب می‌شود، پس -timestamp
        queryset = queryset.order_by(f"-{self.timestamp_field}")

        # اکنون صفحه‌بندی را اعمال می‌کنیم
        return super().paginate_queryset(queryset, request, view)

    def get_paginated_response(self, data):
        """
        Customizes the response to include time range info.
        """
        return Response({
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'count': self.count,
            'limit': self.limit,
            'offset': self.offset,
            'start_time_filter': self.start_time,
            'end_time_filter': self.end_time,
            'results': data
        })

# --- مثال: صفحه‌بندی بر اساس Cursor (برای عملکرد بالاتر در لیست‌های بلند) ---
from rest_framework.pagination import CursorPagination

class CoreCursorPagination(CursorPagination):
    """
    Cursor-based pagination for efficient pagination of large, ordered datasets.
    Requires an 'ordering' field to be set.
    """
    page_size = 50
    cursor_query_param = 'cursor'
    ordering = '-created_at' # ترتیب پیش‌فرض برای مرتب‌سازی cursor
    ordering_fields = ['created_at', 'updated_at', 'id'] # فیلدهایی که می‌توان بر اساس آن‌ها مرتب کرد

    def get_paginated_response(self, data):
        return Response({
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })
