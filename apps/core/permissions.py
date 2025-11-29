# apps/core/permissions.py
from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    فقط مالک (یا کاربر ست‌شده روی آبجکت) می‌تواند تغییر ایجاد کند.
    بقیه فقط متدهای امن (GET, HEAD, OPTIONS) را می‌بینند.
    """

    def has_object_permission(self, request, view, obj):
        # متدهای امن همیشه مجازند
        if request.method in permissions.SAFE_METHODS:
            return True

        # اولویت با فیلد owner
        if hasattr(obj, "owner"):
            return obj.owner == request.user

        # در غیر این صورت فیلد user
        if hasattr(obj, "user"):
            return obj.user == request.user

        # اگر مدل هیچ‌کدام را نداشت، برای ایمنی بهتر است False برگردانیم
        return False