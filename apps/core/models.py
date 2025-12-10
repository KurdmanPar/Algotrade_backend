# core/models.py
from django.db import models

class BaseModel(models.Model):
    """
    یک مدل پایه برای افزودن فیلدهای مشترک created_at و updated_at
    به تمام مدل‌های دیگر.
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Updated At")

    class Meta:
        abstract = True # این باعث می‌شود که جدولی برای این مدل در دیتابیس ساخته نشود