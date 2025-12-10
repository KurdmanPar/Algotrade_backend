# apps/exchanges/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'exchanges'

# تعریف Router برای ViewSetها
router = DefaultRouter()
router.register(r'exchanges', views.ExchangeViewSet, basename='exchange')
router.register(r'exchange-accounts', views.ExchangeAccountViewSet, basename='exchangeaccount')
router.register(r'wallets', views.WalletViewSet, basename='wallet')
router.register(r'wallet-balances', views.WalletBalanceViewSet, basename='walletbalance')
router.register(r'aggregated-portfolios', views.AggregatedPortfolioViewSet, basename='aggregatedportfolio')
router.register(r'aggregated-asset-positions', views.AggregatedAssetPositionViewSet, basename='aggregatedassetposition')
router.register(r'order-history', views.OrderHistoryViewSet, basename='orderhistory')
router.register(r'market-data-candles', views.MarketDataCandleViewSet, basename='marketdatacandle')

urlpatterns = [
    # مسیر اصلی شامل تمام مسیرهای تعریف شده در Router
    path('', include(router.urls)),
    # مسیرهای اختصاصی می‌توانند در اینجا اضافه شوند
    # مثلاً:
    # path('custom-endpoint/', views.CustomView.as_view(), name='custom-endpoint'),
]

# نکته: اگر از ViewSet استفاده نمی‌کنید و فقط از Viewهای کلاسی یا تابعی استفاده می‌کنید،
# باید مسیرها را به صورت مستقیم با path() تعریف کنید.
# مثال:
# urlpatterns = [
#     path('exchanges/', views.ExchangeListCreateView.as_view(), name='exchange-list-create'),
#     path('exchanges/<int:pk>/', views.ExchangeRetrieveUpdateDestroyView.as_view(), name='exchange-detail'),
#     # ... سایر مسیرها
# ]
