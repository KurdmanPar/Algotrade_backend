# apps/backtesting/views.py
from rest_framework import viewsets, permissions
from .models import BacktestRun, BacktestResult
from .serializers import BacktestRunSerializer, BacktestResultSerializer
from apps.core.views import SecureModelViewSet


class BacktestRunViewSet(SecureModelViewSet):
    queryset = BacktestRun.objects.all()  # اضافه شد
    serializer_class = BacktestRunSerializer


class BacktestResultViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = BacktestResult.objects.all()
    serializer_class = BacktestResultSerializer
    permission_classes = [permissions.IsAuthenticated]