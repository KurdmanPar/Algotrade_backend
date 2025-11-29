# apps/exchanges/views.py
from rest_framework import viewsets, permissions
from .models import Exchange, ExchangeAccount, Wallet, WalletBalance, AggregatedPortfolio, AggregatedAssetPosition
from .serializers import (
    ExchangeSerializer, ExchangeAccountSerializer, WalletSerializer,
    WalletBalanceSerializer, AggregatedPortfolioSerializer, AggregatedAssetPositionSerializer
)

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        return True

class ExchangeViewSet(viewsets.ModelViewSet):
    queryset = Exchange.objects.all()
    serializer_class = ExchangeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class ExchangeAccountViewSet(viewsets.ModelViewSet):
    serializer_class = ExchangeAccountSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        return ExchangeAccount.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class WalletViewSet(viewsets.ModelViewSet):
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated]

class WalletBalanceViewSet(viewsets.ModelViewSet):
    queryset = WalletBalance.objects.all()
    serializer_class = WalletBalanceSerializer
    permission_classes = [permissions.IsAuthenticated]

class AggregatedPortfolioViewSet(viewsets.ModelViewSet):
    serializer_class = AggregatedPortfolioSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        return AggregatedPortfolio.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(user=user)

class AggregatedAssetPositionViewSet(viewsets.ModelViewSet):
    queryset = AggregatedAssetPosition.objects.all()
    serializer_class = AggregatedAssetPositionSerializer
    permission_classes = [permissions.IsAuthenticated]
