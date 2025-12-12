# myproject/asgi.py
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import apps.instruments.routing # یا مسیر دیگری که routing.py شما در آن قرار دارد

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            apps.instruments.routing.websocket_urlpatterns # یا مسیرهای دیگر
        )
    ),
})