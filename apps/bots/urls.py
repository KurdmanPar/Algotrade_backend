# apps/bots/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BotViewSet

# یک Router برای مدیریت مسیرهای ViewSet به صورت خودکار
router = DefaultRouter()
router.register(r'bots', BotViewSet, basename='bot')

# urlpatterns لیست تمام مسیرهای این اپلیکیشن را در خود جای می‌دهد
urlpatterns = [
    path('', include(router.urls)),
]