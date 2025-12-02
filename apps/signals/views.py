# apps/signals/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.throttling import UserRateThrottle
from django.utils import timezone
from django.db import transaction
from django_filters import rest_framework as filters
import logging

from .models import Signal, SignalLog, SignalAlert
from .serializers import SignalSerializer, SignalLogSerializer, SignalAlertSerializer

logger = logging.getLogger(__name__)


# -------------------- Throttling --------------------

class SignalCreateThrottle(UserRateThrottle):
    """
    Rate limiting برای جلوگیری از spam سیگنال
    100 سیگنال در ساعت برای هر کاربر
    """
    rate = '100/hour'


# -------------------- Filters --------------------

class SignalFilter(filters.FilterSet):
    """فیلتر امن برای لیست سیگنال‌ها"""
    status = filters.ChoiceFilter(choices=Signal.status.field.choices)
    direction = filters.ChoiceFilter(choices=Signal.direction.field.choices)
    date_from = filters.DateTimeFilter(field_name="generated_at", lookup_expr='gte')
    date_to = filters.DateTimeFilter(field_name="generated_at", lookup_expr='lte')

    class Meta:
        model = Signal
        fields = ['status', 'direction', 'bot', 'strategy_version', 'instrument']


# -------------------- Signal ViewSet --------------------

class SignalViewSet(viewsets.ModelViewSet):
    """
    ViewSet امن برای مدیریت سیگنال‌ها
    فقط CREATE و READ مجاز است - UPDATE و DELETE از طریق ادمین
    """
    queryset = Signal.objects.all()
    serializer_class = SignalSerializer
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [SignalCreateThrottle]
    filterset_class = SignalFilter
    ordering_fields = ['-generated_at', 'status', 'priority']
    ordering = ['-generated_at']

    def get_queryset(self):
        """
        کاربران عادی فقط سیگنال‌های خود را ببینند
        ادمین‌ها همه سیگنال‌ها را می‌بینند
        """
        queryset = Signal.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(user=self.request.user)
        return queryset.select_related(
            'instrument', 'exchange_account', 'bot', 'strategy_version', 'agent'
        )

    def get_serializer_context(self):
        """اضافه کردن IP و request به context برای serializer"""
        context = super().get_serializer_context()
        context['request'] = self.request
        return context

    def create(self, request, *args, **kwargs):
        """ایجاد سیگنال با atomic transaction و لاگ کامل"""
        try:
            with transaction.atomic():
                response = super().create(request, *args, **kwargs)
                signal_id = response.data['id']
                logger.info(
                    f"Signal#{signal_id} created by User#{request.user.id} "
                    f"from IP {self._get_client_ip()}"
                )
                return response
        except Exception as e:
            logger.error(
                f"Signal creation failed for User#{request.user.id}: {str(e)}"
            )
            return Response(
                {"error": "Signal creation failed"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def update(self, request, *args, **kwargs):
        """غیرفعال کردن ویرایش از API"""
        return Response(
            {"error": "Signal update not allowed via API"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def destroy(self, request, *args, **kwargs):
        """غیرفعال کردن حذف از API"""
        return Response(
            {"error": "Signal deletion not allowed via API"},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    @action(detail=True, methods=['post'])
    def acknowledge_alert(self, request, pk=None):
        """تایید هشدار سیگنال توسط کاربر"""
        signal = self.get_object()
        alert_id = request.data.get('alert_id')

        try:
            alert = signal.signal_alerts.get(id=alert_id, is_acknowledged=False)
            alert.acknowledge(request.user, self._get_client_ip())
            return Response({"status": "acknowledged"})
        except SignalAlert.DoesNotExist:
            return Response(
                {"error": "Alert not found or already acknowledged"},
                status=status.HTTP_404_NOT_FOUND
            )

    def _get_client_ip(self) -> str:
        """استخراج IP امن از request"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR', '')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return self.request.META.get('REMOTE_ADDR', '0.0.0.0')


# -------------------- SignalLog ViewSet (ReadOnly) --------------------

class SignalLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet فقط‌خواندنی برای لاگ‌ها
    فقط کاربران احراز شده می‌توانند لاگ سیگنال‌های خود را ببینند
    """
    serializer_class = SignalLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    ordering = ['-created_at']

    def get_queryset(self):
        """کاربر فقط لاگ سیگنال‌های خود را می‌بیند"""
        return SignalLog.objects.filter(
            signal__user=self.request.user
        ).select_related(
            'signal', 'changed_by_agent', 'changed_by_user'
        )


# -------------------- SignalAlert ViewSet (ReadOnly) --------------------

class SignalAlertViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet فقط‌خواندنی برای هشدارها
    کاربر فقط هشدارهای سیگنال‌های خود را می‌بیند
    """
    serializer_class = SignalAlertSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['severity', 'is_acknowledged', 'alert_type']
    ordering = ['-severity', '-created_at']

    def get_queryset(self):
        """کاربر فقط هشدارهای سیگنال‌های خود را می‌بیند"""
        return SignalAlert.objects.filter(
            signal__user=self.request.user
        ).select_related(
            'signal', 'acknowledged_by'
        )