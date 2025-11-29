# apps/exchanges/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'exchanges', views.ExchangeViewSet)
router.register(r'exchange-accounts', views.ExchangeAccountViewSet)
router.register(r'wallets', views.WalletViewSet)
router.register(r'wallet-balances', views.WalletBalanceViewSet)
router.register(r'aggregated-portfolios', views.AggregatedPortfolioViewSet)
router.register(r'aggregated-asset-positions', views.AggregatedAssetPositionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]