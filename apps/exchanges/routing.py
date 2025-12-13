# apps/exchanges/routing.py

from django.urls import path
from . import consumers

websocket_urlpatterns = [
    # مسیرهای WebSocket برای نوتیفیکیشن‌های حساب
    path('ws/exchanges/account-status/', consumers.ExchangeAccountStatusConsumer.as_asgi(), name='ws-account-status'),
    # مسیرهای WebSocket برای تاریخچه سفارشات
    path('ws/exchanges/order-history/', consumers.OrderHistoryConsumer.as_asgi(), name='ws-order-history'),
    # مسیرهای WebSocket برای اعلان‌های عمومی صرافی
    path('ws/exchanges/notifications/', consumers.ExchangeNotificationConsumer.as_asgi(), name='ws-exchange-notifications'),
    # مسیرهای WebSocket برای ارتباط عامل
    path('ws/exchanges/agent-comm/', consumers.AgentCommunicationConsumer.as_asgi(), name='ws-agent-comm'),
    # سایر مسیرهای WebSocket مرتبط با اپلیکیشن exchanges
    # مثلاً:
    # path('ws/exchanges/account-status/<str:account_id>/', consumers.ExchangeAccountStatusConsumer.as_asgi(), name='ws-account-status-detail'),
    # path('ws/exchanges/orders/<str:user_id>/', consumers.OrderHistoryConsumer.as_asgi(), name='ws-user-orders'),
]

logger.info("Exchanges WebSocket routing patterns loaded successfully.")
