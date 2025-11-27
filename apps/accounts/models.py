# apps/accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    """
    مدل کاربر سفارشی پروژه که از ایمیل به عنوان نام کاربری استفاده می‌کند.
    """
    username = None  # نام کاربری پیش‌فرض را غیرفعال می‌کنیم
    email = models.EmailField(unique=True, verbose_name="Email Address")

    # فیلدهای timestamp را فقط با auto_now_add و auto_now تعریف کنید
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # فیلدهای اضافی مورد نیاز
    phone_number = models.CharField(max_length=32, blank=True)
    is_verified = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'  # مشخص کردن ایمیل به عنوان فیلد ورود
    REQUIRED_FIELDS = [] # فیلدهای مورد نیاز هنگام ایجاد سوپر یوزر

    def __str__(self):
        return self.email
