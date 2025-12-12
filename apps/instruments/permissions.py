# apps/instruments/permissions.py

from rest_framework import permissions
from django.core.exceptions import ObjectDoesNotExist
from .models import (
    InstrumentWatchlist,
    # سایر مدل‌هایی که نیاز به کنترل مالکیت یا دسترسی دارند
    # مثلاً: IndicatorTemplate, InstrumentExchangeMap
)

class IsOwnerOfWatchlist(permissions.BasePermission):
    """
    اجازه دسترسی را فقط به مالک یک InstrumentWatchlist می‌دهد.
    این اجازه‌نامه برای عملیات‌هایی استفاده می‌شود که یک شیء InstrumentWatchlist دارند.
    """
    message = 'You must be the owner of this watchlist to perform this action.'

    def has_object_permission(self, request, view, obj):
        """
        بررسی می‌کند که آیا کاربر فعلی مالک شیء Watchlist است یا خیر.
        """
        # فرض بر این است که مدل InstrumentWatchlist دارای یک فیلد 'owner' است که به کاربر متصل می‌شود
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        # اگر فیلد owner وجود نداشت، ممکن است نیاز به منطق دیگری باشد یا این اجازه‌نامه مناسب نباشد.
        # برای این مثال، فرض می‌کنیم فیلد owner وجود دارد.
        return False

    def has_permission(self, request, view):
        """
        بررسی عمومی احراز هویت.
        این فقط زمانی مهم است که `has_object_permission` فراخوانی نشود (مثلاً برای لیست کردن).
        اگر `IsOwnerOfWatchlist` فقط برای عملیات روی یک شیء (retrieve, update, destroy) استفاده شود،
        این متد ممکن است نیاز نباشد، اما برای اطمینان می‌توان آن را گنجاند.
        """
        # معمولاً برای این نوع اجازه، کاربر باید احراز هویت شده باشد.
        return request.user.is_authenticated


class IsOwnerOfIndicatorTemplate(permissions.BasePermission):
    """
    اجازه‌نامه‌ای برای اطمینان از اینکه کاربر مالک یک IndicatorTemplate است.
    """
    message = 'You must be the owner of this indicator template to perform this action.'

    def has_object_permission(self, request, view, obj):
        """
        بررسی می‌کند که آیا کاربر فعلی مالک شیء IndicatorTemplate است یا خیر.
        """
        # فرض بر این است که مدل IndicatorTemplate دارای یک فیلد 'owner' یا 'user' است.
        # اگر فیلد owner استفاده شود:
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        # اگر فیلد user استفاده شود:
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False

    def has_permission(self, request, view):
        return request.user.is_authenticated


class IsOwnerOfRelatedInstrument(permissions.BasePermission):
    """
    اجازه‌نامه‌ای برای اطمینان از اینکه کاربر مالک نماد مرتبط با یک شیء است.
    مثلاً برای یک نظر یا امتیازدهی روی نماد.
    فرض: شیء دارای فیلد 'instrument' است که یک ForeignKey به مدل Instrument دارد،
    و مدل Instrument دارای فیلد 'owner' است.
    """
    message = 'You must be the owner of the related instrument.'

    def has_object_permission(self, request, view, obj):
        """
        بررسی می‌کند که آیا کاربر مالک نماد مرتبط با شیء `obj` است.
        """
        # چک کردن اینکه آیا شیء دارای ویژگی instrument و instrument دارای owner است
        if hasattr(obj, 'instrument') and hasattr(obj.instrument, 'owner'):
            return obj.instrument.owner == request.user
        return False


class IsOwnerOfRelatedUser(permissions.BasePermission):
    """
    اجازه‌نامه‌ای برای اطمینان از اینکه کاربر مالک شیء مرتبط با کاربر است.
    مثلاً برای دسترسی به یک نمایه کاربری خاص.
    فرض: شیء دارای فیلد 'user' است.
    """
    message = 'You must be the owner of the related user profile.'

    def has_object_permission(self, request, view, obj):
        """
        بررسی می‌کند که آیا شیء مرتبط با کاربر `obj.user` متعلق به کاربر فعلی `request.user` است.
        """
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False


class IsAdminUserOrReadOnly(permissions.IsAdminUser):
    """
    اجازه دسترسی فقط برای کاربران ادمین برای عملیات نوشتن.
    کاربران معمولی فقط می‌توانند عملیات خواندن را انجام دهند.
    """
    def has_permission(self, request, view):
        is_admin = super().has_permission(request, view)
        # اجازه برای عملیات خواندن (GET, HEAD, OPTIONS) به همه کاربران احراز هویت شده یا نشده داده می‌شود
        if request.method in permissions.SAFE_METHODS:
            return True
        # فقط کاربران ادمین می‌توانند عملیات نوشتن (POST, PUT, PATCH, DELETE) را انجام دهند
        return is_admin


class IsVerifiedUser(permissions.BasePermission):
    """
    اجازه دسترسی را فقط به کاربران تأیید شده می‌دهد.
    این فرض را می‌کند که مدل کاربر فیلدی مانند `is_verified` دارد.
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


class CanModifyInstrument(permissions.BasePermission):
    """
    اجازه دسترسی را فقط به مجوزهای خاص مدل (Django's built-in permissions) می‌دهد.
    مثلاً فقط کاربرانی که مجوز 'instruments.change_instrument' را دارند.
    """
    message = "You do not have permission to modify this instrument."

    def has_object_permission(self, request, view, obj):
        # فرض بر این است که obj یک نماد (Instrument) است
        # چک کردن مجوز 'change' برای مدل Instrument
        # این مجوزها معمولاً در ادمین جنگو تعریف و به گروه‌ها/کاربران اختصاص داده می‌شود
        return request.user.has_perm('instruments.change_instrument', obj)

class CanViewInstrument(permissions.BasePermission):
    """
    اجازه دسترسی فقط برای مشاهده نماد.
    """
    message = "You do not have permission to view this instrument."

    def has_object_permission(self, request, view, obj):
        # چک کردن مجوز 'view'
        return request.user.has_perm('instruments.view_instrument', obj)


# --- اجازه‌نامه‌های مبتنی بر نقش (Role-Based) ---
# این بخش نیازمند پیاده‌سازی سیستم نقش‌ها (مثلاً با django-guardian یا یک فیلد role در مدل کاربر) است.
# مثال ساده با فیلد role در مدل کاربر:
# class HasRole(permissions.BasePermission):
#     """
#     اجازه‌نامه‌ای برای بررسی نقش کاربر.
#     """
#     required_roles = [] # باید در نماها یا فایل‌های دیگر تعریف شود
#
#     def has_permission(self, request, view):
#         if request.user.is_authenticated:
#             return request.user.role in self.required_roles
#         return False
#
# class IsTrader(HasRole):
#     required_roles = ['trader', 'admin']
#
# class IsAnalyst(HasRole):
#     required_roles = ['analyst', 'admin']


# --- مثال: اجازه‌نامه‌ای برای دسترسی به منابع عمومی یا مالک آن ---
class IsPublicOrOwner(permissions.BasePermission):
    """
    اجازه دسترسی به منابعی که دارای فیلد is_public هستند.
    اگر منبع عمومی باشد، همه می‌توانند بخوانند. اگر خصوصی باشد، فقط مالک می‌تواند دسترسی داشته باشد.
    """
    message = "This resource is private and you do not own it."

    def has_object_permission(self, request, view, obj):
        # اطمینان از اینکه شیء دارای فیلدهای مورد نیاز است
        if hasattr(obj, 'is_public') and hasattr(obj, 'owner'):
            if obj.is_public:
                # اگر عمومی بود، فقط دسترسی خواندن مجاز است
                if request.method in permissions.SAFE_METHODS:
                    return True
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
