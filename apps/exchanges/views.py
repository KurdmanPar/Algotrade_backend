# apps/exchanges/views.py
from rest_framework import viewsets, permissions
from .models import (
    Exchange,
    ExchangeAccount,
    Wallet,
    WalletBalance,
    AggregatedPortfolio,
    AggregatedAssetPosition
)
from .serializers import (
    ExchangeSerializer,
    ExchangeAccountSerializer,
    WalletSerializer,
    WalletBalanceSerializer,
    AggregatedPortfolioSerializer,
    AggregatedAssetPositionSerializer
)
from apps.core.views import SecureModelViewSet


class ExchangeViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = Exchange.objects.all()
    serializer_class = ExchangeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class ExchangeAccountViewSet(SecureModelViewSet):
    queryset = ExchangeAccount.objects.all()  # اضافه شد
    serializer_class = ExchangeAccountSerializer


class WalletViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]


class WalletBalanceViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = WalletBalance.objects.all()
    serializer_class = WalletBalanceSerializer
    permission_classes = [permissions.IsAuthenticated]


class AggregatedPortfolioViewSet(SecureModelViewSet):
    queryset = AggregatedPortfolio.objects.all()  # اضافه شد
    serializer_class = AggregatedPortfolioSerializer


class AggregatedAssetPositionViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = AggregatedAssetPosition.objects.all()
    serializer_class = AggregatedAssetPositionSerializer
    permission_classes = [permissions.IsAuthenticated]