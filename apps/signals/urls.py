# apps/signals/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'signals', views.SignalViewSet)
router.register(r'signal-logs', views.SignalLogViewSet)
router.register(r'signal-alerts', views.SignalAlertViewSet)

urlpatterns = [
    path('', include(router.urls)),
]