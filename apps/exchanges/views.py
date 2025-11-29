# apps/exchanges/views.py
from rest_framework import viewsets, permissions
from .models import Exchange, ExchangeAccount, Wallet, WalletBalance, AggregatedPortfolio, AggregatedAssetPosition
from .serializers import (
    ExchangeSerializer, ExchangeAccountSerializer, WalletSerializer,
    WalletBalanceSerializer, AggregatedPortfolioSerializer, AggregatedAssetPositionSerializer
)
from apps.core.views import SecureModelViewSet  # اضافه کنید

class ExchangeViewSet(SecureModelViewSet):
    queryset = Exchange.objects.all()
    serializer_class = ExchangeSerializer
    # دیگر نیازی به تعریف permission_classes نیست، چون از SecureModelViewSet ارث می‌برد

class ExchangeAccountViewSet(SecureModelViewSet):
    queryset = ExchangeAccount.objects.all()
    serializer_class = ExchangeAccountSerializer
    # فیلتر خودکار بر اساس owner در SecureModelViewSet انجام می‌شود

class WalletViewSet(SecureModelViewSet):
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer

class WalletBalanceViewSet(SecureModelViewSet):
    queryset = WalletBalance.objects.all()
    serializer_class = WalletBalanceSerializer

class AggregatedPortfolioViewSet(SecureModelViewSet):
    queryset = AggregatedPortfolio.objects.all()
    serializer_class = AggregatedPortfolioSerializer

class AggregatedAssetPositionViewSet(SecureModelViewSet):
    queryset = AggregatedAssetPosition.objects.all()
    serializer_class = AggregatedAssetPositionSerializer