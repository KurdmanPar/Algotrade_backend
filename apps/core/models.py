# apps/core/models.py
from django.db import models

class BaseModel(models.Model):
    """یک مدل پایه برای اضافه کردن فیلدهای timestamp به تمام مدل‌ها"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True # این باعث می‌شود که جدولی برای این مدل در دیتابیس ساخته نشود