# tests/test_exchanges/test_permissions.py

import pytest
from rest_framework.permissions import SAFE_METHODS
from apps.exchanges.models import ExchangeAccount, Wallet, OrderHistory
from apps.exchanges.permissions import IsOwnerOfExchangeAccount, IsOwnerOfAggregatedPortfolio
from django.test import RequestFactory

pytestmark = pytest.mark.django_db


class TestExchangePermissions:
    def test_is_owner_of_exchange_account(self, ExchangeAccountFactory, CustomUserFactory):
        owner_user = CustomUserFactory()
        other_user = CustomUserFactory()
        account = ExchangeAccountFactory(user=owner_user)

        perm = IsOwnerOfExchangeAccount()

        # ساخت یک request شبیه‌سازی شده
        request = type('MockRequest', (), {'user': owner_user})()

        # تست اجازه دسترسی برای مالک
        assert perm.has_object_permission(request, None, account) is True

        # تست عدم اجازه دسترسی برای کاربر دیگر
        request.user = other_user
        assert perm.has_object_permission(request, None, account) is False

    # سایر تست‌های اجازه‌نامه‌ها...
