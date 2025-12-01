# apps/market_data/views.py
from rest_framework import viewsets, permissions
from .models import (
    DataSource,
    MarketDataConfig,
    MarketDataSnapshot,
    MarketDataSyncLog
)
from .serializers import (
    DataSourceSerializer,
    MarketDataConfigSerializer,
    MarketDataSnapshotSerializer,
    MarketDataSyncLogSerializer
)
from apps.core.views import SecureModelViewSet


class DataSourceViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = DataSource.objects.all()
    serializer_class = DataSourceSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class MarketDataConfigViewSet(SecureModelViewSet):
    queryset = MarketDataConfig.objects.all()  # اضافه شد
    serializer_class = MarketDataConfigSerializer


class MarketDataSnapshotViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = MarketDataSnapshot.objects.all()
    serializer_class = MarketDataSnapshotSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    # می‌توانید از اینجا فیلتر کنید، مثلاً با پارامترهای کوئری
    def get_queryset(self):
        qs = MarketDataSnapshot.objects.all()
        instrument_id = self.request.query_params.get('instrument_id', None)
        if instrument_id:
            qs = qs.filter(config__instrument_id=instrument_id)
        return qs


class MarketDataSyncLogViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = MarketDataSyncLog.objects.all()
    serializer_class = MarketDataSyncLogSerializer
    permission_classes = [permissions.IsAuthenticated]