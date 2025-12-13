# apps/exchanges/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'exchanges'

# تعریف Router برای ViewSetها
router = DefaultRouter()
router.register(r'exchanges', views.ExchangeViewSet, basename='exchange')
router.register(r'exchange-accounts', views.ExchangeAccountViewSet, basename='exchange-account')
router.register(r'wallets', views.WalletViewSet, basename='wallet')
router.register(r'wallet-balances', views.WalletBalanceViewSet, basename='wallet-balance')
router.register(r'aggregated-portfolios', views.AggregatedPortfolioViewSet, basename='aggregated-portfolio')
router.register(r'aggregated-asset-positions', views.AggregatedAssetPositionViewSet, basename='aggregated-asset-position')
router.register(r'order-history', views.OrderHistoryViewSet, basename='order-history')
router.register(r'market-data-candles', views.MarketDataCandleViewSet, basename='market-data-candle')

urlpatterns = [
    # مسیر اصلی شامل تمام مسیرهای تعریف شده در Router
    path('', include(router.urls)),

    # مسیرهای اختصاصی می‌توانند در اینجا اضافه شوند
    # مثلاً:
    # path('custom-endpoint/', views.CustomView.as_view(), name='custom-endpoint'),
    # path('search/', views.InstrumentSearchView.as_view(), name='instrument-search'),
    # path('health-check/', views.HealthCheckView.as_view(), name='health-check'),
    # path('ping/', views.PingView.as_view(), name='ping'),

    # مثال: اضافه کردن مسیرهای اختصاصی برای نماهایی که در views.py تعریف شده‌اند
    # path('instrument-stats/<str:symbol>/', views.InstrumentStatsView.as_view(), name='instrument-stats'),
    # path('calculate-indicator/', views.CalculateIndicatorView.as_view(), name='calculate-indicator'),
]

# نکته: اگر از ViewSet استفاده نمی‌کنید و فقط از Viewهای کلاسی یا تابعی استفاده می‌کنید،
# باید مسیرها را به صورت مستقیم با path() تعریف کنید.
# مثال:
# urlpatterns = [
#     path('exchanges/', views.ExchangeListCreateView.as_view(), name='exchange-list-create'),
#     path('exchanges/<int:pk>/', views.ExchangeRetrieveUpdateDestroyView.as_view(), name='exchange-detail'),
#     path('exchange-accounts/', views.ExchangeAccountListCreateView.as_view(), name='exchange-account-list-create'),
#     path('exchange-accounts/<uuid:pk>/', views.ExchangeAccountRetrieveUpdateDestroyView.as_view(), name='exchange-account-detail'),
#     # ... سایر مسیرها
# ]

logger.info("Exchanges URL patterns loaded successfully.")
