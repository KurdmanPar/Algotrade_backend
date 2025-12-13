# apps/exchanges/permissions.py

from rest_framework import permissions
from django.core.exceptions import ObjectDoesNotExist
from apps.core.permissions import IsOwnerOrReadOnly # فرض بر این است که این اجازه‌نامه وجود دارد و در core تعریف شده است
from apps.core.exceptions import CoreSystemException, SecurityException # فرض بر این است که این استثناها وجود دارند
from .models import (
    ExchangeAccount,
    Wallet,
    WalletBalance,
    OrderHistory,
    AggregatedPortfolio,
    AggregatedAssetPosition,
    # سایر مدل‌های exchanges
)

logger = logging.getLogger(__name__)

# --- اجازه‌نامه‌های مرتبط با مالکیت (Ownership) ---
# این اجازه‌نامه‌ها با توجه به BaseOwnedModel از core، بر اساس فیلد 'owner' عمل می‌کنند، نه 'user'

class IsOwnerOfExchangeAccount(permissions.BasePermission):
    """
    Custom permission to only allow the owner of an ExchangeAccount to access it.
    This is crucial for security as exchange accounts contain sensitive API keys.
    Assumes the model has an 'owner' field inherited from BaseOwnedModel.
    """
    message = 'You must be the owner of this exchange account to perform this action.'

    def has_object_permission(self, request, view, obj):
        """
        Checks if the requesting user is the owner of the object.
        Works for ExchangeAccount, Wallet, WalletBalance, OrderHistory, AggregatedPortfolio, AggregatedAssetPosition
        if they have an 'owner' field or a related object with an 'owner' field.
        """
        # 1. اگر شیء دارای فیلد 'owner' مستقیم بود (مثل ExchangeAccount یا AggregatedPortfolio)
        if hasattr(obj, 'owner'):
            return obj.owner == request.user

        # 2. اگر شیء دارای فیلد مرتبط با شیء دیگری بود که فیلد 'owner' داشت (مثل Wallet -> ExchangeAccount)
        if hasattr(obj, 'exchange_account') and hasattr(obj.exchange_account, 'owner'):
            return obj.exchange_account.owner == request.user

        # 3. اگر شیء دارای فیلد مرتبط با شیء دیگری بود که فیلد 'owner' داشت (مثل WalletBalance -> Wallet -> ExchangeAccount)
        if hasattr(obj, 'wallet') and hasattr(obj.wallet, 'exchange_account') and hasattr(obj.wallet.exchange_account, 'owner'):
            return obj.wallet.exchange_account.owner == request.user

        # 4. اگر شیء دارای فیلد مرتبط با شیء دیگری بود که فیلد 'owner' داشت (مثل OrderHistory -> ExchangeAccount)
        if hasattr(obj, 'exchange_account') and hasattr(obj.exchange_account, 'owner'):
            return obj.exchange_account.owner == request.user

        # 5. اگر شیء دارای فیلد مرتبط با شیء دیگری بود که فیلد 'owner' داشت (مثل AggregatedAssetPosition -> AggregatedPortfolio)
        if hasattr(obj, 'aggregated_portfolio') and hasattr(obj.aggregated_portfolio, 'owner'):
            return obj.aggregated_portfolio.owner == request.user

        # اگر فیلد owner یا رابطه مالکیت پیدا نشد، اجازه را رد می‌کنیم
        return False

    def has_permission(self, request, view):
        """
        Basic check to ensure the user is authenticated.
        The specific object-level check happens in has_object_permission.
        """
        return request.user.is_authenticated


class IsOwnerOfRelatedExchangeAccount(permissions.BasePermission):
    """
    Custom permission to only allow the owner of a *related* ExchangeAccount to access an object.
    Useful for models like Wallet, WalletBalance, OrderHistory that are linked to an ExchangeAccount.
    """
    message = 'You must be the owner of the related exchange account to perform this action.'

    def has_object_permission(self, request, view, obj):
        """
        Checks if the requesting user is the owner of the related ExchangeAccount.
        Assumes the object has an 'exchange_account' ForeignKey field.
        """
        if hasattr(obj, 'exchange_account') and hasattr(obj.exchange_account, 'owner'):
            return obj.exchange_account.owner == request.user
        return False

    def has_permission(self, request, view):
        return request.user.is_authenticated


class IsOwnerOfAggregatedPortfolio(permissions.BasePermission):
    """
    Custom permission to only allow the owner of an AggregatedPortfolio to access it.
    Assumes the model has an 'owner' field.
    """
    message = 'You must be the owner of this aggregated portfolio to perform this action.'

    def has_object_permission(self, request, view, obj):
        """
        Checks if the requesting user is the owner of the AggregatedPortfolio object.
        """
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        return False

    def has_permission(self, request, view):
        return request.user.is_authenticated


class IsOwnerOfRelatedAggregatedPortfolio(permissions.BasePermission):
    """
    Custom permission to only allow the owner of a *related* AggregatedPortfolio to access an object.
    Useful for models like AggregatedAssetPosition.
    """
    message = 'You must be the owner of the related aggregated portfolio to perform this action.'

    def has_object_permission(self, request, view, obj):
        """
        Checks if the requesting user is the owner of the related AggregatedPortfolio.
        Assumes the object has an 'aggregated_portfolio' ForeignKey field.
        """
        if hasattr(obj, 'aggregated_portfolio') and hasattr(obj.aggregated_portfolio, 'owner'):
            return obj.aggregated_portfolio.owner == request.user
        return False

    def has_permission(self, request, view):
        return request.user.is_authenticated


# --- اجازه‌نامه‌های مرتبط با وضعیت و مجوزها ---
class IsAccountActive(permissions.BasePermission):
    """
    Permission to check if the related ExchangeAccount is active.
    """
    message = 'The related exchange account is not active.'

    def has_object_permission(self, request, view, obj):
        # این می‌تواند برای هر شیء مرتبط با ExchangeAccount استفاده شود
        if hasattr(obj, 'exchange_account'):
            return obj.exchange_account.is_active
        elif hasattr(obj, 'owner'): # برای خود ExchangeAccount
            return obj.is_active
        return True # اگر رابطه‌ای نبود، فقط احراز هویت مهم است


class HasAPIAccessPermission(permissions.BasePermission):
    """
    Permission to check if the user has API access enabled in their profile.
    Assumes the user model has a related profile with 'api_access_enabled' field.
    """
    message = 'API access is not enabled for your account.'

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        try:
            profile = request.user.profile
            return profile.api_access_enabled
        except AttributeError:
            logger.error(f"User {request.user.email} does not have a profile for API access check.")
            return False # یا True بسته به policy - اگر پروفایل نبود، ممکن است دسترسی پیش‌فرض نداشته باشند


class IsAccountPaperTrading(permissions.BasePermission):
    """
    Permission to check if the related ExchangeAccount is a paper trading account.
    """
    message = 'This action is only allowed on paper trading accounts.'

    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'exchange_account'):
            return obj.exchange_account.is_paper_trading
        elif hasattr(obj, 'owner'): # برای خود ExchangeAccount
            return obj.is_paper_trading
        return False # یا True بسته به نیاز - اگر رابطه‌ای نبود


# --- اجازه‌نامه‌های مرتبط با IP Whitelist ---
class IsIPWhitelisted(permissions.BasePermission):
    """
    Permission to check if the client IP is whitelisted for the user's profile.
    """
    message = 'Your IP address is not whitelisted for this action.'

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        try:
            profile = request.user.profile
            allowed_ips_str = profile.allowed_ips
            if not allowed_ips_str:
                # اگر لیست IPها خالی بود، فرض می‌کنیم همه IPها مجاز هستند
                return True

            client_ip = self.get_client_ip(request)
            allowed_ips_list = [item.strip() for item in allowed_ips_str.split(',') if item.strip()]
            from apps.core.helpers import is_ip_in_allowed_list # import داخل تابع
            is_allowed = is_ip_in_allowed_list(client_ip, allowed_ips_list)
            if is_allowed:
                 logger.debug(f"IP {client_ip} is whitelisted for user {request.user.email}.")
                 return True
            else:
                 logger.warning(f"IP {client_ip} is NOT whitelisted for user {request.user.email}.")
                 return False
        except AttributeError:
            logger.error(f"User {request.user.email} does not have a profile for IP whitelist check.")
            return False # یا True - بسته به policy
        except Exception as e:
            logger.error(f"Error checking IP whitelist for user {request.user.email}: {str(e)}")
            return False # برای امنیت، در صورت خطا، دسترسی رد می‌شود

    def get_client_ip(self, request):
        """
        Extracts the real client IP, considering proxies.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# --- اجازه‌نامه‌های مرتبط با نقش (Role-Based) (اگر سیستم نقش داشته باشیم) ---
# این بخش نیازمند پیاده‌سازی سیستم نقش‌ها (مثلاً با django-guardian یا یک فیلد role در مدل کاربر) است.
# مثال ساده با فیلد role در مدل کاربر:
# class HasRole(permissions.BasePermission):
#     """
#     Permission class for checking user role.
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
#
# class IsDeveloper(HasRole):
#     required_roles = ['developer', 'admin']

# --- اجازه‌نامه‌های مرتبط با مجوز (Permission-Based) ---
# این نوع اجازه‌نامه‌ها با استفاده از مجوزهای داخلی جنگو (model-level, object-level permissions) کار می‌کنند.
# مثلاً اگر مدل Instrument دارای مجوزهای خاصی باشند:
# class CanViewInstrument(permissions.BasePermission):
#     """
#     Permission based on Django's built-in model permissions (view_instrument).
#     """
#     message = "You do not have permission to view this instrument."
#
#     def has_object_permission(self, request, view, obj):
#         # چک کردن مجوز 'view' برای مدل Instrument
#         # این مجوزها معمولاً در ادمین جنگو تعریف و به گروه‌ها/کاربران اختصاص داده می‌شود
#         return request.user.has_perm('instruments.view_instrument', obj)
#
# class CanModifyInstrument(permissions.BasePermission):
#     """
#     Permission based on Django's built-in model permissions (change_instrument).
#     """
#     message = "You do not have permission to modify this instrument."
#
#     def has_object_permission(self, request, view, obj):
#         return request.user.has_perm('instruments.change_instrument', obj)

# --- اجازه‌نامه‌های ترکیبی (Combination of Permissions) ---
# می‌توانید از `django-braces` یا ترکیب دستی استفاده کنید
# from rest_framework.permissions import BasePermission
# class CombinedPermission(BasePermission):
#     def has_permission(self, request, view):
#         # مثال: احراز هویت + تأیید شده بودن + عضویت در گروه
#         return (
#             request.user.is_authenticated and
#             request.user.is_verified and
#             request.user.groups.filter(name='VerifiedTraders').exists()
#         )
#     def has_object_permission(self, request, view, obj):
#         # مثال: مالکیت + وضعیت فعال
#         return (
#             IsOwnerOrReadOnly().has_object_permission(request, view, obj) and
#             obj.is_active
#         )

# --- مثال: اجازه‌نامه برای دسترسی به داده‌های عمومی یا مالک آن ---
class IsPublicOrOwnerOfExchangeAccount(permissions.BasePermission):
    """
    Permission to allow access to public exchange account info or owned account info.
    Assumes the model has 'is_public' and 'owner' fields.
    """
    message = 'This exchange account is private and you do not own it.'

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

logger.info("Exchanges permissions loaded successfully.")
