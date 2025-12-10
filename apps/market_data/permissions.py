# apps/market_data/permissions.py

from rest_framework import permissions
from .models import MarketDataConfig, DataSource # فرض بر این است که مدل‌ها وجود دارند


class IsOwnerOfMarketDataConfig(permissions.BasePermission):
    """
    اجازه‌نامه‌ای برای اطمینان از اینکه کاربر فقط به کانفیگ‌های داده‌ای که متعلق به نمادهایی است که مالک آن‌ها است، دسترسی دارد.
    این فرض می‌کند که نماد (Instrument) دارای یک فیلد `owner` است که به کاربر متصل می‌شود.
    """
    def has_object_permission(self, request, view, obj):
        # obj یک نمونه از MarketDataConfig است
        if isinstance(obj, MarketDataConfig):
            # دسترسی به کانفیگ مربوط به نمادی است که کاربر مالک آن است
            return obj.instrument.owner == request.user
        # اگر obj از نوع دیگری بود، می‌توان از روش‌های دیگری استفاده کرد یا False برگرداند
        return False

    def has_permission(self, request, view):
        # اطمینان از احراز هویت کاربر
        return request.user.is_authenticated

class HasReadAccessToDataSource(permissions.BasePermission):
    """
    اجازه‌نامه‌ای برای کنترل دسترسی خواندن به DataSource.
    در اینجا می‌توان منطقی مانند بررسی نقش (Role) یا مجوز (Permission) کاربر پیاده‌سازی کرد.
    مثلاً فقط کاربران با گروه 'data_readers' می‌توانند DataSourceها را بخوانند.
    """
    def has_permission(self, request, view):
        if view.action in ['list', 'retrieve']: # فقط برای عملیات‌های خواندنی
            # بررسی اینکه آیا کاربر دارای مجوز خاصی است یا در گروه خاصی قرار دارد
            # مثال: return request.user.groups.filter(name='data_readers').exists()
            # یا: return request.user.has_perm('market_data.can_read_datasource')
            # برای مثال ساده، فقط احراز هویت کافی است
            return request.user.is_authenticated
        # برای سایر عملیات، مجوزهای دیگری ممکن است لازم باشد
        return request.user.is_authenticated

# سایر اجازه‌نامه‌های مورد نیاز می‌توانند در این فایل اضافه شوند
# مثلاً IsOwnerOfMarketDataSnapshot، IsAdminOrReadOnly و غیره
