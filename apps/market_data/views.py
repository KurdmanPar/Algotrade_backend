# apps/market_data/views.py
from rest_framework import viewsets, permissions
from .models import DataSource, MarketDataConfig, MarketDataSyncLog, MarketDataSnapshot
from .serializers import *

class MarketDataViewSetBase:
    permission_classes = [permissions.IsAuthenticated]

class DataSourceViewSet(viewsets.ModelViewSet, MarketDataViewSetBase):
    queryset = DataSource.objects.all()
    serializer_class = DataSourceSerializer

class MarketDataConfigViewSet(viewsets.ModelViewSet, MarketDataViewSetBase):
    queryset = MarketDataConfig.objects.all()
    serializer_class = MarketDataConfigSerializer

class MarketDataSyncLogViewSet(viewsets.ModelViewSet, MarketDataViewSetBase):
    queryset = MarketDataSyncLog.objects.all()
    serializer_class = MarketDataSyncLogSerializer

class MarketDataSnapshotViewSet(viewsets.ModelViewSet, MarketDataViewSetBase):
    queryset = MarketDataSnapshot.objects.all()
    serializer_class = MarketDataSnapshotSerializer