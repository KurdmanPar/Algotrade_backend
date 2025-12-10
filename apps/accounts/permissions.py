# apps/accounts/permissions.py

from rest_framework import permissions
from django.utils import timezone
from .models import UserAPIKey, UserProfile

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD, or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the object.
        # Assuming the object has a 'user' attribute that links to the owner
        return hasattr(obj, 'user') and obj.user == request.user

class IsOwnerOfUser(permissions.BasePermission):
    """
    Custom permission to only allow a user to access their own profile/session/key data.
    """
    def has_object_permission(self, request, view, obj):
        # Check if the object has a 'user' attribute linking to the owner
        if hasattr(obj, 'user'):
            return obj.user == request.user
        # For CustomUser objects themselves
        elif hasattr(obj, 'id'):
            return obj.id == request.user.id
        return False

class HasAPIAccess(permissions.BasePermission):
    """
    Custom permission to check if the user has API access enabled in their profile
    and the specific API key is valid and active.
    """
    def has_permission(self, request, view):
        # Check if user is authenticated via session (for UI access)
        if request.user.is_authenticated:
            # For UI, check if API access is enabled in profile
            try:
                profile = request.user.profile
                return profile.api_access_enabled
            except UserProfile.DoesNotExist:
                return False

        # Check if user is authenticated via API key (for API access)
        api_key_string = request.META.get('HTTP_X_API_KEY') # یا هر هدر دیگری که کلید را منتقل می‌کند
        if api_key_string:
            try:
                api_key = UserAPIKey.objects.get(key=api_key_string, is_active=True)
                if api_key.is_valid() and api_key.user.profile.api_access_enabled: # فرض بر این است که متد is_valid در مدل تعریف شده یا در اینجا پیاده‌سازی شود
                    # بخشی از منطق rate limiting نیز می‌تواند اینجا یا در یک middleware اعمال شود
                    # api_key.update_last_used() # به روزرسانی آخرین زمان استفاده
                    request.user = api_key.user # تنظیم کاربر در درخواست
                    return True
            except UserAPIKey.DoesNotExist:
                pass
        return False

    def has_object_permission(self, request, view, obj):
        # می‌توانید منطق خاصی برای دسترسی به یک شیء خاص توسط API Key نیز اضافه کنید
        # برای سادگی، فقط بررسی می‌کنیم که آیا کاربر از طریق API Key احراز هویت شده است یا خیر
        # و این که آیا آن شیء متعلق به همان کاربر است.
        if hasattr(obj, 'user'):
            return hasattr(request, 'user') and obj.user == request.user
        return True # یا منطق مناسب دیگر

class IsVerifiedUser(permissions.BasePermission):
    """
    Custom permission to only allow verified users.
    """
    def has_permission(self, request, view):
        if request.user.is_authenticated:
            return request.user.is_verified
        return False

    def has_object_permission(self, request, view, obj):
        # اگر نیاز به چک کردن شی خاصی باشد
        # فرض بر این است که شیء متعلق به کاربر است و کاربر تأیید شده است
        if request.user.is_authenticated and request.user.is_verified:
            if hasattr(obj, 'user'):
                return obj.user == request.user
            elif hasattr(obj, 'id'):
                return obj.id == request.user.id
        return False
