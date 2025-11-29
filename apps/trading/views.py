# apps/trading/views.py
from rest_framework import viewsets, permissions
from .models import Order, Trade, Position, OrderLog
from .serializers import *
from apps.core.views import SecureModelViewSet

class OrderViewSet(SecureModelViewSet):
    queryset = Order.objects.all()  # اضافه شود
    serializer_class = OrderSerializer

class TradeViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = Trade.objects.all()
    serializer_class = TradeSerializer
    permission_classes = [permissions.IsAuthenticated]

class PositionViewSet(SecureModelViewSet):
    queryset = Position.objects.all()  # اضافه شود
    serializer_class = PositionSerializer

class OrderLogViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = OrderLog.objects.all()
    serializer_class = OrderLogSerializer
    permission_classes = [permissions.IsAuthenticated]