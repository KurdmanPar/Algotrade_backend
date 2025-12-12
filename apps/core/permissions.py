# apps/core/permissions.py

from rest_framework import permissions
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import AnonymousUser
from .models import BaseOwnedModel # فرض بر این است که مدل‌های پایه در core قرار دارند

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    اجازه دسترسی را فقط به مالک یک شیء می‌دهد.
    فقط مالک می‌تواند عملیات نوشتن (PUT, PATCH, DELETE) را انجام دهد.
    بقیه کاربران احراز هویت شده فقط می‌توانند عملیات خواندن (GET, HEAD, OPTIONS) را انجام دهند.
    کاربران ناشناس به هیچ عملیاتی دسترسی ندارند.
    این اجازه‌نامه برای مدل‌هایی استفاده می‌شود که دارای فیلد 'owner' (ForeignKey به User) هستند.
    """
    message = 'You must be the owner of this object to perform this action.'

    def has_object_permission(self, request, view, obj):
        """
        بررسی می‌کند که آیا کاربر فعلی مالک شیء `obj` است یا خیر.
        """
        # چک کردن اینکه آیا شیء دارای فیلد 'owner' است یا خیر
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        # اگر فیلد owner وجود نداشت، اجازه را رد می‌کنیم
        # این اجازه‌نامه فقط برای مدل‌هایی با فیلد owner مناسب است
        return False

    def has_permission(self, request, view):
        """
        بررسی عمومی احراز هویت.
        اگر کاربر احراز هویت نشده باشد، دسترسی ندارد.
        """
        # فقط کاربران احراز هویت شده می‌توانند درخواست ارسال کنند
        # برای عملیات‌های خواندن، این کافی است. برای نوشتن، has_object_permission چک می‌شود.
        return request.user.is_authenticated


class IsOwnerOfRelatedObject(permissions.BasePermission):
    """
    اجازه‌نامه‌ای برای اطمینان از اینکه کاربر مالک یک شیء مرتبط است.
    مثلاً: یک کاربر فقط بتواند نظر خود را روی یک نماد ویرایش یا حذف کند.
    فرض: شیء دارای یک فیلد مانند 'instrument' یا 'user' است که به یک مدل دیگر با فیلد 'owner' متصل است.
    """
    message = 'You must be the owner of the related object to perform this action.'

    def has_object_permission(self, request, view, obj):
        """
        بررسی می‌کند که آیا کاربر فعلی مالک شیء مرتبط با `obj` است یا خیر.
        """
        # مثال: اگر obj یک نظر (Comment) باشد و دارای فیلد 'instrument' باشد
        # که یک ForeignKey به مدل Instrument (که دارای فیلد owner است) باشد.
        related_obj_attr = getattr(obj, 'instrument', None) # تغییر دهید: نام فیلد مرتبط
        if related_obj_attr and hasattr(related_obj_attr, 'owner'):
            return related_obj_attr.owner == request.user

        # مثال دیگر: اگر obj دارای فیلد 'user' باشد که به کاربر مربوطه است.
        related_user_attr = getattr(obj, 'user', None) # تغییر دهید: نام فیلد مرتبط
        if related_user_attr:
             return related_user_attr == request.user

        # اگر فیلد مرتبط یا owner وجود نداشت، دسترسی رد می‌شود.
        return False

    def has_permission(self, request, view):
        # فقط کاربران احراز هویت شده می‌توانند درخواست ارسال کنند
        return request.user.is_authenticated


class IsAdminUserOrReadOnly(permissions.IsAdminUser):
    """
    اجازه دسترسی فقط برای کاربران ادمین برای عملیات نوشتن.
    کاربران معمولی فقط می‌توانند عملیات خواندن را انجام دهند.
    """
    def has_permission(self, request, view):
        is_admin = super().has_permission(request, view)
        # اجازه برای عملیات خواندن (GET, HEAD, OPTIONS) به همه کاربران احراز هویت شده داده می‌شود
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated # فقط احراز هویت لازم است
        # فقط کاربران ادمین می‌توانند عملیات نوشتن (POST, PUT, PATCH, DELETE) را انجام دهند
        return is_admin


class IsVerifiedUser(permissions.BasePermission):
    """
    اجازه دسترسی را فقط به کاربران تأیید شده می‌دهد.
    این فرض را می‌کند که مدل کاربر فیلد `is_verified` دارد.
    """
    message = 'Your account must be verified to access this resource.'

    def has_permission(self, request, view):
        # بررسی احراز هویت
        if not request.user.is_authenticated:
            return False
        # بررسی تأیید حساب
        user_model = request.user.__class__
        if hasattr(user_model, 'is_verified'):
             return request.user.is_verified
        else:
             # اگر فیلد وجود نداشت، فقط بررسی is_authenticated کافی است یا خطایی را صادر کنید
             # برای سادگی، فقط is_authenticated را چک می‌کنیم
             return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # اگر نیاز به بررسی مالکیت شیء نیست، فقط تأیید کاربر تأیید شده کافی است
        return self.has_permission(request, view)


class CanModifyBasedOnPermissions(permissions.BasePermission):
    """
    اجازه دسترسی را بر اساس مجوزهای (Permissions) خاص مدل (Django's built-in permissions) می‌دهد.
    مثلاً فقط کاربرانی که مجوز 'instruments.change_instrument' را دارند.
    """
    # می‌توانید این فیلد را در نماها یا فایل‌های دیگر تنظیم کنید
    required_perms = [] # e.g., ['instruments.change_instrument']

    def has_permission(self, request, view):
        # فقط کاربران احراز هویت شده
        if not request.user.is_authenticated:
            return False
        # اگر لیست مجوزهای مورد نیاز تعریف نشده بود، فقط احراز هویت کافی است
        if not self.required_perms:
            return True
        # چک کردن همه مجوزهای لازم
        for perm in self.required_perms:
            if not request.user.has_perm(perm):
                return False
        return True

    def has_object_permission(self, request, view, obj):
        # اگر نیاز باشد، مجوزهای شیء-محور نیز چک شود
        # این فقط زمانی فراخوانی می‌شود که has_permission True برگرداند
        # اینجا می‌توانید منطقی مانند obj.owner == request.user یا چک کردن مجوزهای شیء-محور اضافه کنید
        # در این مثال، فقط چک کردن مجوزهای کلی کافی است
        return self.has_permission(request, view)


class IsPublicOrOwner(permissions.BasePermission):
    """
    اجازه دسترسی به منابعی که دارای فیلد is_public هستند.
    اگر منبع عمومی باشد، همه کاربران احراز هویت شده می‌توانند بخوانند.
    اگر خصوصی باشد، فقط مالک می‌تواند دسترسی داشته باشد.
    فقط مالک می‌تواند ویرایش یا حذف کند.
    """
    message = "This resource is private and you do not own it."

    def has_object_permission(self, request, view, obj):
        # اطمینان از اینکه شیء دارای فیلدهای مورد نیاز است
        if hasattr(obj, 'is_public') and hasattr(obj, 'owner'):
            if obj.is_public:
                # اگر عمومی بود، فقط دسترسی خواندن برای کاربران احراز هویت شده مجاز است
                if request.method in permissions.SAFE_METHODS:
                    return request.user.is_authenticated
                else:
                    # اگر عمومی بود، فقط مالک می‌تواند تغییر دهد
                    return obj.owner == request.user
            else:
                # اگر خصوصی بود، فقط مالک می‌تواند دسترسی داشته باشد
                return obj.owner == request.user
        # اگر فیلدها وجود نداشتند، اجازه را رد می‌کنیم
        return False

    def has_permission(self, request, view):
        # احراز هویت عمومی برای همه درخواست‌ها الزامی است
        return request.user.is_authenticated

# --- مثال: اجازه‌نامه‌ای برای دسترسی به منابع مربوط به یک عامل خاص (در سیستم MAS) ---
# این نیازمند این است که شیء دارای یک ارتباط با یک عامل (Agent) باشد
# class IsOwnerOfRelatedAgent(permissions.BasePermission):
#     message = "You must be the owner of the related agent."
#
#     def has_object_permission(self, request, view, obj):
#         if hasattr(obj, 'agent') and hasattr(obj.agent, 'owner'):
#             return obj.agent.owner == request.user
#         return False
#
#     def has_permission(self, request, view):
#         return request.user.is_authenticated

# --- مثال: اجازه‌نامه مبتنی بر نقش (اگر سیستم نقش داشته باشد) ---
# class HasRole(permissions.BasePermission):
#     required_roles = [] # باید در نماها یا کلاس‌های دیگر تعریف شود
#
#     def has_permission(self, request, view):
#         if request.user.is_authenticated:
#             return getattr(request.user, 'role', None) in self.required_roles
#         return False
#
# class IsTrader(HasRole):
#     required_roles = ['trader', 'admin']
#
# class IsAnalyst(HasRole):
#     required_roles = ['analyst', 'admin']
