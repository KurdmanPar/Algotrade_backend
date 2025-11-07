# backend/trading/tests/test_api.py

import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from django.urls import reverse


@pytest.fixture
def api_client():
    """یک fixture برای کلاینت API بدون احراز هویت."""
    return APIClient()


@pytest.fixture
def authenticated_user(api_client):
    """
    یک fixture برای ایجاد یک کاربر و احراز هویت آن در api_client.
    این fixture یک دیکشنری برمی‌گرداند که شامل کلاینت و آبجکت کاربر است.
    """
    user = get_user_model().objects.create_user(
        username='testuser',
        password='testpass123',
        email='test@example.com'
    )
    api_client.force_authenticate(user=user)
    return {'client': api_client, 'user': user}


# --- تست‌های مربوط به کاربران ---

@pytest.mark.django_db
def test_user_list_as_authenticated_user(authenticated_user):
    """
    تست لیست کاربران توسط یک کاربر احراز هویت شده
    """
    url = reverse('user-list')
    response = authenticated_user['client'].get(url)

    assert response.status_code == 200
    # بررسی می‌کنیم که لیست حاوی حداقل یک کاربر (همان کاربر لاگین کرده) باشد
    assert len(response.data) >= 1


@pytest.mark.django_db
def test_user_create(api_client):
    """
    تست ایجاد کاربر جدید (نیازی به احراز هویت ندارد)
    """
    url = reverse('user-list')
    data = {
        'username': 'newuser',
        'email': 'newuser@example.com',
        'password': 'newpass123'
    }
    response = api_client.post(url, data)

    assert response.status_code == 201
    assert get_user_model().objects.filter(username='newuser').exists()


@pytest.mark.django_db
def test_user_list_as_anonymous_user(api_client):
    """
    تست اینکه کاربر ناشناس نباید به لیست کاربران دسترسی داشته باشد
    """
    url = reverse('user-list')
    response = api_client.get(url)

    assert response.status_code == 403  # Forbidden


# --- تست‌های مربوط به استراتژی‌ها ---

@pytest.mark.django_db
def test_create_strategy_as_authenticated_user(authenticated_user):
    """
    تست ایجاد یک استراتژی جدید توسط کاربر احراز هویت شده
    """
    url = reverse('strategy-list')
    data = {
        'name': 'Test Strategy',
        'description': 'A simple test strategy',
        'type': 'custom'
    }
    response = authenticated_user['client'].post(url, data)

    assert response.status_code == 201
    assert response.data['name'] == 'Test Strategy'
    # بررسی می‌کنیم که owner به درستی روی کاربر لاگین شده تنظیم شده باشد
    assert response.data['owner'] == authenticated_user['user'].id


@pytest.mark.django_db
def test_list_strategies_as_authenticated_user(authenticated_user):
    """
    تست اینکه کاربر فقط لیست استراتژی‌های خودش را می‌بیند
    """
    # ایجاد یک استراتژی برای کاربر اصلی
    from trading.models import Strategy
    Strategy.objects.create(
        name='User Strategy',
        owner=authenticated_user['user'],
        type='custom'
    )

    # ایجاد یک استراتژی برای کاربر دیگر
    other_user = get_user_model().objects.create_user(username='otheruser', password='pass')
    Strategy.objects.create(
        name='Other User Strategy',
        owner=other_user,
        type='predefined'
    )

    url = reverse('strategy-list')
    response = authenticated_user['client'].get(url)

    assert response.status_code == 200
    # کاربر باید فقط استراتژی خودش را ببیند
    assert len(response.data) == 1
    assert response.data[0]['name'] == 'User Strategy'


@pytest.mark.django_db
def test_create_strategy_as_anonymous_user(api_client):
    """
    تست اینکه کاربر ناشناس نباید بتواند استراتژی بسازد
    """
    url = reverse('strategy-list')
    data = {
        'name': 'Should not be created',
        'type': 'custom'
    }
    response = api_client.post(url, data)

    assert response.status_code == 403  # Forbidden


#############################################################
#############################################################


# --- تست‌های مربوط به بات‌ها ---

@pytest.mark.django_db
def test_create_bot_as_authenticated_user(authenticated_user):
    """
    تست ایجاد یک بات جدید توسط کاربر احراز هویت شده
    """
    # ابتدا یک استراتژی برای کاربر ایجاد می‌کنیم
    from trading.models import Strategy
    strategy = Strategy.objects.create(
        name='Test Strategy for Bot',
        owner=authenticated_user['user'],
        type='custom'
    )

    url = reverse('bot-list')
    data = {
        'name': 'Test Bot',
        'strategy': strategy.id,  # ارسال آیدی استراتژی
        'symbol': 'BTCUSDT',
        'exchange': 'binance'
    }
    response = authenticated_user['client'].post(url, data)

    assert response.status_code == 201
    assert response.data['name'] == 'Test Bot'
    assert response.data['user'] == authenticated_user['user'].id
    assert response.data['strategy'] == strategy.id



@pytest.mark.django_db
def test_list_bots_as_authenticated_user(authenticated_user):
    """
    تست اینکه کاربر فقط لیست بات‌های خودش را می‌بیند
    """
    # ایجاد یک بات برای کاربر اصلی
    from trading.models import Bot, Strategy
    strategy = Strategy.objects.create(owner=authenticated_user['user'], name='Strategy 1', type='custom')
    # نیازی به ارسال start_time نیست چون auto_now_add دارد
    Bot.objects.create(
        name='User Bot',
        user=authenticated_user['user'],
        strategy=strategy,
        symbol='BTCUSDT',
        exchange='binance'
    )

    # ایجاد یک بات برای کاربر دیگر
    other_user = get_user_model().objects.create_user(username='otherbotuser', password='pass')
    other_strategy = Strategy.objects.create(owner=other_user, name='Strategy 2', type='predefined')
    Bot.objects.create(
        name='Other User Bot',
        user=other_user,
        strategy=other_strategy,
        symbol='ETHUSDT',
        exchange='binance'
    )

    url = reverse('bot-list')
    response = authenticated_user['client'].get(url)

    assert response.status_code == 200
    # کاربر باید فقط بات خودش را ببیند
    assert len(response.data) == 1
    assert response.data[0]['name'] == 'User Bot'


# ... سایر تست‌ها ...

@pytest.mark.django_db
def test_create_bot_as_anonymous_user(api_client):
    """
    تست اینکه کاربر ناشناس نباید بتواند بات بسازد
    """
    url = reverse('bot-list')
    data = {
        'name': 'Should not be created',
        'symbol': 'BTCUSDT',
        'exchange': 'binance'
    }
    response = api_client.post(url, data)

    assert response.status_code == 403  # Forbidden