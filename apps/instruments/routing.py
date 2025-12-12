# apps/instruments/routing.py

from django.urls import path
from . import consumers

websocket_urlpatterns = [
    # مسیر برای دریافت داده بازار نمادهای مختلف
    # مثال: ws://localhost:8000/ws/instruments/market-data/
    path('ws/instruments/market-data/', consumers.MarketDataConsumer.as_asgi(), name='ws-market-data'),
    # مسیر برای اعلان‌های مربوط به نماد
    # مثال: ws://localhost:8000/ws/instruments/notifications/
    path('ws/instruments/notifications/', consumers.InstrumentNotificationConsumer.as_asgi(), name='ws-instrument-notifications'),
    # مسیر برای ارتباط با عامل‌های مرتبط با نماد (اختیاری و پیشرفته)
    # path('ws/instruments/agent-comm/', consumers.AgentCommunicationConsumer.as_asgi(), name='ws-agent-comm'),
    # ... سایر مسیرهای WebSocket مرتبط با ابزارها ...
]
