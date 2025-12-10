# apps/market_data/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'market_data'

# تعریف Router برای ViewSetها
router = DefaultRouter()
router.register(r'data-sources', views.DataSourceViewSet, basename='datasource')
router.register(r'market-data-configs', views.MarketDataConfigViewSet, basename='marketdataconfig')
router.register(r'market-data-snapshots', views.MarketDataSnapshotViewSet, basename='marketdatasnapshot')
router.register(r'market-data-order-books', views.MarketDataOrderBookViewSet, basename='marketdataorderbook')
router.register(r'market-data-ticks', views.MarketDataTickViewSet, basename='marketdatatick')
router.register(r'market-data-sync-logs', views.MarketDataSyncLogViewSet, basename='marketdatasynclog')
router.register(r'market-data-caches', views.MarketDataCacheViewSet, basename='marketdatacache')

urlpatterns = [
    # مسیر اصلی شامل تمام مسیرهای تعریف شده در Router
    path('', include(router.urls)),

    # مسیرهای اختصاصی می‌توانند در اینجا اضافه شوند
    # مثلاً:
    # path('custom-endpoint/', views.CustomView.as_view(), name='custom-endpoint'),
    # path('instrument/<str:symbol>/latest-snapshot/', views.LatestSnapshotView.as_view(), name='latest-snapshot'),
    # path('instrument/<str:symbol>/latest-order-book/', views.LatestOrderBookView.as_view(), name='latest-order-book'),
    # path('instrument/<str:symbol>/latest-tick/', views.LatestTickView.as_view(), name='latest-tick'),
]

# نکته: اگر از ViewSet استفاده نمی‌کنید و فقط از Viewهای کلاسی یا تابعی استفاده می‌کنید،
# باید مسیرها را به صورت مستقیم با path() تعریف کنید.
# مثال:
# urlpatterns = [
#     path('data-sources/', views.DataSourceListCreateView.as_view(), name='datasource-list-create'),
#     path('data-sources/<int:pk>/', views.DataSourceRetrieveUpdateDestroyView.as_view(), name='datasource-detail'),
#     # ... سایر مسیرها
# ]
