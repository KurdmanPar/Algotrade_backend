# apps/backtesting/views.py
from rest_framework import viewsets, permissions
from .models import BacktestRun, BacktestResult
from .serializers import BacktestRunSerializer, BacktestResultSerializer

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.owner == request.user

class BacktestRunViewSet(viewsets.ModelViewSet):
    # اضافه کردن queryset
    queryset = BacktestRun.objects.all()
    serializer_class = BacktestRunSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        # فقط بک‌تست‌های کاربر فعلی را نشان بده
        return BacktestRun.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        # مالک را به طور خودکار تنظیم کن
        serializer.save(owner=self.request.user)

class BacktestResultViewSet(viewsets.ModelViewSet):
    # اضافه کردن queryset
    queryset = BacktestResult.objects.all()
    serializer_class = BacktestResultSerializer
    permission_classes = [permissions.IsAuthenticated]