# apps/signals/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SignalViewSet, SignalLogViewSet, SignalAlertViewSet

router = DefaultRouter()
router.register(r'signals', SignalViewSet, basename='signal')
router.register(r'signal-logs', SignalLogViewSet, basename='signal-log')  # فقط‌خواندنی
router.register(r'signal-alerts', SignalAlertViewSet, basename='signal-alert')  # فقط‌خواندنی

urlpatterns = [
    path('', include(router.urls)),
]