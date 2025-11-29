# apps/bots/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'bots', views.BotViewSet)
router.register(r'bot-strategy-configs', views.BotStrategyConfigViewSet)
router.register(r'bot-logs', views.BotLogViewSet)
router.register(r'bot-performance-snapshots', views.BotPerformanceSnapshotViewSet)

urlpatterns = [
    path('', include(router.urls)),
]