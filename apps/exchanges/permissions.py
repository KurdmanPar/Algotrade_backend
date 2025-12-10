# apps/exchanges/permissions.py

from rest_framework import permissions
from .models import ExchangeAccount


class IsOwnerOfExchangeAccount(permissions.BasePermission):
    """
    Custom permission to only allow the owner of an ExchangeAccount to access it.
    This is crucial for security as exchange accounts contain sensitive API keys.
    """
    def has_object_permission(self, request, view, obj):
        # Check if the object has a 'user' attribute linking to the owner
        # This works for ExchangeAccount, Wallet, WalletBalance, OrderHistory
        if hasattr(obj, 'exchange_account'):
            return obj.exchange_account.user == request.user
        # For ExchangeAccount objects themselves
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        # For AggregatedPortfolio and AggregatedAssetPosition
        elif hasattr(obj, 'aggregated_portfolio') and hasattr(obj.aggregated_portfolio, 'user'):
            return obj.aggregated_portfolio.user == request.user
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        return False

    def has_permission(self, request, view):
        # Basic check to ensure the user is authenticated
        # The specific object-level check happens in has_object_permission
        return request.user.is_authenticated

class IsOwnerOfAggregatedPortfolio(permissions.BasePermission):
    """
    Custom permission to only allow the owner of an AggregatedPortfolio to access it.
    """
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'user'):
            return obj.user == request.user
        return False

    def has_permission(self, request, view):
        return request.user.is_authenticated

# سایر اجازه‌نامه‌های خاص می‌توانند در اینجا اضافه شوند
# مثلاً اجازه‌نامه‌ای برای کاربران با دسترسی خاص یا بر اساس نقش (Role-based)
