# tests/conftest.py
import pytest
from django.conf import settings
from django.test import RequestFactory
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    اطمینان از اینکه تمام تست‌ها می‌توانند به پایگاه داده دسترسی داشته باشند.
    """
    pass

@pytest.fixture
def rf():
    """
    یک نمونه از RequestFactory.
    """
    return RequestFactory()

@pytest.fixture
def sample_user():
    """
    یک کاربر نمونه.
    """
    return User.objects.create_user(
        email="test@example.com",
        password="strongpassword123",
        username_display="TestUser"
    )