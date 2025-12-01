# apps/market_data/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'data-sources', views.DataSourceViewSet)
router.register(r'market-data-configs', views.MarketDataConfigViewSet)
router.register(r'market-data-snapshots', views.MarketDataSnapshotViewSet)
router.register(r'market-data-sync-logs', views.MarketDataSyncLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
]