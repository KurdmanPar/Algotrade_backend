# apps/core/routing.py

from django.urls import path
from . import consumers

# --- مسیرهای WebSocket برای Core ---
# این مسیرها فقط شامل مصرف‌کننده‌های عمومی یا پایه‌ای Core می‌شوند
# مسیرهای مربوط به دامنه‌های خاص (مثل instruments, trading, agents) باید در اپلیکیشن مربوطه قرار گیرند

websocket_urlpatterns = [
    # مثال: چنل عمومی برای اعلان‌های سیستم یا سلامت سیستم
    # path('ws/core/system-notifications/', consumers.CoreNotificationConsumer.as_asgi(), name='ws-core-notifications'),

    # مثال: چنل عمومی برای وضعیت کلی سیستم
    # path('ws/core/system-status/', consumers.CoreSystemStatusConsumer.as_asgi(), name='ws-core-status'),

    # مثال: چنل عمومی برای لاگ‌های سیستم (اگر نیاز باشد و امن باشد)
    # path('ws/core/system-logs/', consumers.CoreSystemLogConsumer.as_asgi(), name='ws-core-logs'),

    # مسیرهای مربوط به سایر مصرف‌کننده‌های Core ...
]

# --- مسیرهای عمومی برای MAS ---
# می‌توانید چنل‌هایی برای ارتباط عمومی بین عامل‌ها (Agents) یا سایر بخش‌های سیستم تعریف کنید
# مثال:
# path('ws/mas/global-events/', consumers.GlobalMASConsumer.as_asgi(), name='ws-mas-global-events'),

# --- نکات مهم ---
# 1. مسیرها باید با مسیرهایی که در ASGI اصلی پروژه (myproject/asgi.py) ثبت می‌شوند مطابقت داشته باشند.
# 2. معمولاً مسیرهای اصلی WebSocket در ASGI اصلی با یک پیشوند (مثل 'ws/') شروع می‌شوند.
#    مسیرهای اینجا معمولاً نسبی هستند و به آن پیشوند اضافه می‌شوند.
#    مثلاً: 'ws/market-data/<str:symbol>/', 'ws/agent-status/<str:agent_id>/'
# 3. Consumerها باید از کلاس مناسب (مثلاً `AsyncWebsocketConsumer`) ارث ببرند.
# 4. احراز هویت و اجازه‌نامه‌ها معمولاً در خود Consumer انجام می‌شود (در متد `connect`).

# --- مثال ساختار کلی ASGI اصلی ---
# myproject/asgi.py
# from django.core.asgi import get_asgi_application
# from channels.routing import ProtocolTypeRouter, URLRouter
# from channels.auth import AuthMiddlewareStack
# import apps.core.routing
# import apps.market_data.routing # مسیرهای دامنه‌ای
# import apps.agents.routing # مسیرهای دامنه‌ای
#
# application = ProtocolTypeRouter({
#     "http": get_asgi_application(),
#     "websocket": AuthMiddlewareStack( # احراز هویت WebSocket
#         URLRouter(
#             apps.core.routing.websocket_urlpatterns + # مسیرهای Core
#             apps.market_data.routing.websocket_urlpatterns + # مسیرهای دامنه‌ای
#             apps.agents.routing.websocket_urlpatterns + # مسیرهای دامنه‌ای
#             # سایر مسیرهای WebSocket
#         )
#     ),
# })

logger.info("Core WebSocket routing patterns loaded successfully.")
