# tests/test_exchanges/test_views.py

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from apps.exchanges.models import ExchangeAccount, OrderHistory
from apps.exchanges.serializers import ExchangeAccountSerializer

pytestmark = pytest.mark.django_db


class TestExchangeAccountViewSet:
    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def authenticated_api_client(self, api_client, CustomUserFactory):
        user = CustomUserFactory()
        api_client.force_authenticate(user=user)
        return api_client, user

    def test_list_exchange_accounts_authenticated(self, authenticated_api_client, ExchangeAccountFactory):
        client, user = authenticated_api_client
        # ایجاد چند حساب برای کاربر فعلی
        ExchangeAccountFactory.create_batch(3, user=user)
        # ایجاد یک حساب برای کاربر دیگر
        ExchangeAccountFactory()

        url = reverse('exchanges:exchangeaccount-list') # توجه کنید که app_name باید در URLconf اصلی تنظیم شده باشد
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # فقط حساب‌های کاربر فعلی باید بازگردانده شوند
        assert len(response.data) == 3

    def test_create_exchange_account_authenticated(self, authenticated_api_client, ExchangeFactory):
        client, user = authenticated_api_client
        exchange = ExchangeFactory()

        url = reverse('exchanges:exchangeaccount-list')
        data = {
            'exchange': exchange.id,
            'label': 'My New Account',
            'api_key': 'new_key_123',
            'api_secret': 'new_secret_456',
            'is_active': True,
        }
        response = client.post(url, data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert ExchangeAccount.objects.filter(user=user, label='My New Account').exists()

    # سایر تست‌های نماها...
