# apps/core/consumers.py

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from .exceptions import (
    CoreSystemException,
    AuthenticationError,
    AuthorizationError,
    SubscriptionError,
)
from .services import SecurityService # فرض بر این است که وجود دارد
from .helpers import get_client_ip, generate_device_fingerprint # فرض بر این است که وجود دارند
from apps.accounts.models import CustomUser # فرض بر این است که مدل وجود دارد

User = get_user_model()
logger = logging.getLogger(__name__)

class SecureWebSocketConsumer(AsyncWebsocketConsumer):
    """
    Base consumer class for secure WebSocket connections.
    Handles authentication, authorization, and common message parsing.
    """
    async def connect(self):
        """
        Called when a WebSocket connection is initiated.
        Performs authentication and authorization checks.
        """
        user = self.scope.get("user", None)
        if user is None or not user.is_authenticated:
            await self.close(code=4001) # کد خطای سفارشی برای عدم احراز هویت
            return

        # چک کردن IP Whitelist (اگر در پروفایل کاربر وجود داشت)
        client_ip = get_client_ip(self.scope['headers'])
        if not await self._is_ip_allowed_for_user(user, client_ip):
            await self.close(code=4003) # کد خطای سفارشی برای IP غیرمجاز
            return

        # چک کردن Device Fingerprint (اختیاری، نیاز به ذخیره فینگرپرینت در سشن/کوکی کاربر دارد)
        # device_fp = generate_device_fingerprint(self.scope)
        # if not await self._is_device_fingerprint_allowed(user, device_fp):
        #     await self.close(code=4004) # کد خطای سفارشی برای دستگاه غیرمجاز
        #     return

        # اطمینان از اینکه WebSocket چنل برای کاربر ایجاد شده است
        self.user = user
        self.channels = set() # مجموعه چنل‌هایی که کاربر به آن‌ها متصل است

        await self.accept()

        logger.info(f"WebSocket connected for user {self.user.email} from IP {client_ip}.")

    async def disconnect(self, close_code):
        """
        Called when the WebSocket connection is closed.
        Cleans up subscriptions.
        """
        for channel in self.channels.copy(): # استفاده از copy برای جلوگیری از تغییر مجموعه در حین حلقه
            await self.channel_layer.group_discard(
                channel,
                self.channel_name
            )
        self.channels.clear()
        logger.info(f"WebSocket disconnected for user {self.user.email} with code {close_code}.")

    async def receive(self, text_data=None, bytes_data=None):
        """
        Called when a message is received from the WebSocket client.
        Parses the message and handles subscription/unsubscription requests.
        """
        try:
            if text_data:
                 data = json.loads(text_data)
            else:
                 # اگر bytes_data وجود داشت، ممکن است نیاز به دیکد کردن باشد
                 # data = json.loads(bytes_data.decode('utf-8'))
                 logger.warning(f"Received binary data from user {self.user.email}, ignoring.")
                 return

            message_type = data.get("type") # مثلاً 'subscribe', 'unsubscribe', 'ping', 'pong'
            payload = data.get("payload", {}) # بقیه داده

            if message_type == "subscribe":
                await self.handle_subscribe(payload)
            elif message_type == "unsubscribe":
                await self.handle_unsubscribe(payload)
            elif message_type == "ping":
                await self.send(text_data=json.dumps({"type": "pong", "timestamp": timezone.now().isoformat()}))
            elif message_type == "pong":
                # می‌توانید heartbeat را مدیریت کنید
                pass
            else:
                # می‌توانید از یک متد عمومی برای پردازش پیام‌های سفارشی استفاده کنید
                await self.handle_custom_message(message_type, payload)

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received from user {self.user.email}.")
            await self.send(text_data=json.dumps({"error": "Invalid JSON format."}))
        except Exception as e:
            logger.error(f"Error processing WebSocket message for user {self.user.email}: {str(e)}")
            await self.send(text_data=json.dumps({"error": "An internal error occurred while processing your message."}))
            # در صورت نیاز، اتصال را ببندید
            # await self.close()

    async def handle_subscribe(self, payload):
        """
        Handles a subscription request from the client.
        Payload example: {"channel": "market_data.BINANCE.BTCUSDT.1m"}
        """
        channel_name = payload.get("channel")
        if not channel_name:
            await self.send(text_data=json.dumps({"error": "Channel name is required for subscription."}))
            return

        # اعتبارسنجی نام چنل (اختیاری، اما توصیه می‌شود)
        if not self._is_valid_channel_name(channel_name):
            await self.send(text_data=json.dumps({"error": "Invalid channel name."}))
            return

        # چک کردن مجوز دسترسی کاربر به چنل (مثلاً آیا می‌تواند داده این نماد را ببیند؟)
        if not await self._user_has_access_to_channel(self.user, channel_name):
            await self.send(text_data=json.dumps({"error": "You do not have permission to subscribe to this channel."}))
            return

        # اضافه کردن کاربر به چنل
        await self.channel_layer.group_add(
            channel_name,
            self.channel_name
        )
        self.channels.add(channel_name)

        logger.info(f"User {self.user.email} subscribed to WebSocket channel '{channel_name}'.")

        await self.send(text_data=json.dumps({"message": f"Subscribed to {channel_name}"}))

    async def handle_unsubscribe(self, payload):
        """
        Handles an unsubscription request from the client.
        Payload example: {"channel": "market_data.BINANCE.BTCUSDT.1m"}
        """
        channel_name = payload.get("channel")
        if not channel_name:
            await self.send(text_data=json.dumps({"error": "Channel name is required for unsubscription."}))
            return

        if channel_name not in self.channels:
            await self.send(text_data=json.dumps({"error": "You are not subscribed to this channel."}))
            return

        await self.channel_layer.group_discard(
            channel_name,
            self.channel_name
        )
        self.channels.discard(channel_name)

        logger.info(f"User {self.user.email} unsubscribed from WebSocket channel '{channel_name}'.")

        await self.send(text_data=json.dumps({"message": f"Unsubscribed from {channel_name}"}))

    async def handle_custom_message(self, message_type, payload):
        """
        Override this method in subclasses to handle custom message types.
        """
        logger.warning(f"Received unknown message type '{message_type}' from user {self.user.email}. Ignoring.")

    def _is_valid_channel_name(self, channel_name: str) -> bool:
        """
        Validates the format of a channel name (e.g., using regex).
        Example: market_data.<exchange>.<symbol>.<interval>
        """
        import re
        pattern = r'^[\w.-]+$' # فقط حروف، اعداد، خط تیره، نقطه، زیرخط
        return bool(re.match(pattern, channel_name))

    @database_sync_to_async
    def _user_has_access_to_channel(self, user, channel_name: str) -> bool:
        """
        Checks if a user has permission to subscribe to a specific channel.
        This is a placeholder logic. Implement based on your system's permissions.
        e.g., check if user owns an exchange account for that exchange/symbol.
        """
        # مثال ساده: چک کردن اینکه آیا چنل شامل نمادی است که کاربر دسترسی دارد
        # این نیازمند تجزیه channel_name و بررسی دسترسی است
        # مثلاً: اگر چنل 'market_data.BINANCE.BTCUSDT.1m' بود،
        # چک کنید که آیا کاربر حسابی در Binance دارد که به BTCUSDT دسترسی داشته باشد؟
        # یا آیا نماد BTCUSDT عمومی است؟
        # این منطق بسیار پیچیده است و به معماری دسترسی کاربر به نمادها/صرافی‌ها بستگی دارد
        # برای مثال ساده، فقط کاربر احراز هویت شده را مجاز می‌کنیم
        return user.is_authenticated

    @database_sync_to_async
    def _is_ip_allowed_for_user(self, user, client_ip) -> bool:
        """
        Checks if the client's IP is allowed based on the user's profile.
        Uses the helper function from core.
        """
        try:
            profile = user.profile
            allowed_ips_str = profile.allowed_ips
            if allowed_ips_str:
                 from .helpers import validate_ip_list, is_ip_in_allowed_list # import داخل تابع
                 allowed_ips_list = validate_ip_list(allowed_ips_str)
                 if allowed_ips_list:
                      return is_ip_in_allowed_list(client_ip, allowed_ips_list)
                 else:
                      # اگر لیست IPها نامعتبر بود، بهتر است دسترسی را رد کنیم
                      logger.warning(f"Invalid IP list format for user {user.email}. Denying access.")
                      return False
            return True # اگر لیست خالی بود، فرض می‌کنیم همه IPها مجازند
        except AttributeError: # اگر پروفایل وجود نداشت یا فیلد allowed_ips نبود
             logger.error(f"User {user.email} does not have a profile or allowed_ips field for IP check.")
             return False # برای امنیت، در صورت نبود پروفایل یا فیلد، دسترسی رد می‌شود
        except Exception as e:
             logger.error(f"Error checking IP whitelist for user {user.email} from IP {client_ip}: {str(e)}")
             return False # برای امنیت، در صورت خطا، دسترسی رد می‌شود


# --- مثال: Consumer برای داده‌های بازار ---
class MarketDataConsumer(SecureWebSocketConsumer):
    """
    Consumer for handling real-time market data WebSocket connections.
    Inherits security checks from SecureWebSocketConsumer.
    """
    async def market_data_update(self, event):
        """
        Called when a message is sent to this consumer's channel via channel_layer.group_send().
        Sends the received data to the WebSocket client.
        """
        # گرفتن داده از رویداد
        data = event['data']

        # ارسال داده به کلاینت
        await self.send(text_data=json.dumps(data))

    async def agent_status_update(self, event):
        """
        Called when an agent status update is sent via channel_layer.
        """
        data = event['data']
        await self.send(text_data=json.dumps(data))

    async def trade_execution_update(self, event):
        """
        Called when a trade execution update is sent via channel_layer.
        """
        data = event['data']
        await self.send(text_data=json.dumps(data))

    # می‌توانید سایر انواع پیام‌ها را نیز در اینجا اضافه کنید
    # مثلاً:
    # async def risk_alert(self, event):
    #     data = event['data']
    #     await self.send(text_data=json.dumps(data))

# --- مثال: Consumer برای مدیریت وضعیت عامل (Agent) ---
class AgentStatusConsumer(SecureWebSocketConsumer):
    """
    Consumer for receiving and broadcasting agent status updates.
    """
    async def agent_status_change(self, event):
        """
        Handles agent status change events.
        """
        agent_status_data = event['data']
        await self.send(text_data=json.dumps(agent_status_data))

# --- مثال: Consumer برای مدیریت سیگنال‌های معاملاتی ---
class TradingSignalConsumer(SecureWebSocketConsumer):
    """
    Consumer for receiving and broadcasting trading signals.
    """
    async def trading_signal(self, event):
        """
        Handles incoming trading signal events.
        """
        signal_data = event['data']
        await self.send(text_data=json.dumps(signal_data))

# --- مثال: Consumer برای مدیریت اعلان‌ها ---
class NotificationConsumer(SecureWebSocketConsumer):
    """
    Consumer for sending real-time notifications to the user.
    """
    async def notification_message(self, event):
        """
        Handles incoming notification messages.
        """
        notification_data = event['data']
        await self.send(text_data=json.dumps(notification_data))

logger.info("Core WebSocket consumers loaded successfully.")
