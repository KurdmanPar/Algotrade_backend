# apps/instruments/consumers.py

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings
from apps.core.exceptions import CoreConsumerError
from apps.core.logging import get_logger # فرض بر این است که یک سیستم لاگ مرکزی دارید
from .services import InstrumentService # فرض بر این است که سرویس وجود دارد
from .models import Instrument, InstrumentExchangeMap
from apps.connectors.service import ConnectorService # فرض بر این است که این سرویت وجود دارد
from apps.core.messaging import MessageBus # فرض بر این است که یک سیستم پیام‌رسانی وجود دارد

logger = get_logger(__name__)

class MarketDataConsumer(AsyncWebsocketConsumer):
    """
    ASGI Consumer for handling real-time market data WebSocket connections.
    This consumer listens for subscriptions from clients and forwards real-time data to them.
    It can interact with the InstrumentService and MessageBus.
    """
    async def connect(self):
        """
        Called when a WebSocket connection is initiated.
        Authenticates the user and accepts/rejects the connection.
        """
        # 1. احراز هویت کاربر (اگر لازم باشد)
        # این کار معمولاً با استفاده از scope و Middleware انجام می‌شود
        user = self.scope.get("user", None)
        if user is None or not user.is_authenticated:
            # اگر نیاز به احراز هویت داشته باشید، اتصال را رد کنید
            await self.close(code=4001) # کد سفارشی یا استاندارد
            return

        # 2. پذیرش اتصال
        await self.accept()

        # 3. مقداردهی اولیه
        self.subscribed_channels = set() # ذخیره کانال‌های اشتراک کاربر
        self.user = user
        logger.info(f"WebSocket connected for user {self.user.username}.")


    async def disconnect(self, close_code):
        """
        Called when the WebSocket connection is closed.
        Cleans up subscriptions.
        """
        # 1. لغو اشتراک‌ها در کانال‌های چنل‌های Channels
        for channel in self.subscribed_channels.copy(): # کپی چون ممکن است در حین حلقه، آیتم حذف شود
            await self.channel_layer.group_discard(
                channel,
                self.channel_name
            )
        self.subscribed_channels.clear()

        logger.info(f"WebSocket disconnected for user {self.user.username} with code {close_code}.")


    async def receive(self, text_data=None, bytes_data=None):
        """
        Called when a message is received from the WebSocket client.
        Parses the message and handles subscription/unsubscription requests.
        """
        try:
            # 1. تجزیه JSON
            if text_data:
                 data = json.loads(text_data)
            else:
                 # اگر bytes_data وجود داشت، ممکن است نیاز به دیکد کردن باشد
                 # data = json.loads(bytes_data.decode('utf-8'))
                 logger.warning(f"Received binary data from user {self.user.username}, ignoring.")
                 return

            message_type = data.get("type") # مثلاً 'subscribe', 'unsubscribe'
            symbol = data.get("symbol") # مثلاً 'BTCUSDT'
            exchange = data.get("exchange") # مثلاً 'BINANCE'
            data_type = data.get("data_type", "ticker") # مثلاً 'ticker', 'kline_1m', 'depth'

            if message_type == "subscribe":
                if not symbol or not exchange:
                    await self.send(text_data=json.dumps({"error": "Symbol and exchange are required for subscription."}))
                    return

                # 2. اعتبارسنجی نماد و صرافی (اختیاری، می‌تواند در سرویس انجام شود)
                is_valid = await self._validate_subscription(symbol, exchange, data_type)
                if not is_valid:
                     await self.send(text_data=json.dumps({"error": f"Invalid subscription request for {symbol} on {exchange} with type {data_type}."}))
                     return

                # 3. تولید نام گروه چنل (مثلاً 'market_data.BINANCE.BTCUSDT.ticker')
                group_name = f"market_data.{exchange}.{symbol}.{data_type}"

                # 4. اضافه شدن به گروه چنل
                await self.channel_layer.group_add(
                    group_name,
                    self.channel_name
                )
                self.subscribed_channels.add(group_name)

                logger.info(f"User {self.user.username} subscribed to {group_name}.")

                # 5. ارسال تأیید به کلاینت
                await self.send(text_data=json.dumps({"message": f"Subscribed to {group_name}"}))

            elif message_type == "unsubscribe":
                if not symbol or not exchange:
                    await self.send(text_data=json.dumps({"error": "Symbol and exchange are required for unsubscription."}))
                    return

                group_name = f"market_data.{exchange}.{symbol}.{data_type}"
                await self.channel_layer.group_discard(
                    group_name,
                    self.channel_name
                )
                self.subscribed_channels.discard(group_name)

                logger.info(f"User {self.user.username} unsubscribed from {group_name}.")
                await self.send(text_data=json.dumps({"message": f"Unsubscribed from {group_name}"}))

            else:
                await self.send(text_data=json.dumps({"error": f"Unknown message type: {message_type}"}))

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received from user {self.user.username}.")
            await self.send(text_data=json.dumps({"error": "Invalid JSON format."}))
        except Exception as e:
            logger.error(f"Error processing WebSocket message for user {self.user.username}: {str(e)}")
            await self.send(text_data=json.dumps({"error": "An internal error occurred while processing your request."}))


    async def market_data_update(self, event):
        """
        Called when a message is sent to this consumer's channel via channel_layer.group_send().
        This is how real-time data pushed from other parts of the system (e.g., DataCollectorAgent via MessageBus)
        reaches the connected WebSocket clients.
        """
        # 1. گرفتن داده از رویداد
        data = event['data'] # فرض بر این است که داده در کلید 'data' قرار دارد
        # ممکن است نیاز به ارسال کلیدهای دیگری مانند 'type' یا 'symbol' نیز باشد
        # message = {
        #     'type': event.get('type', 'market_data'),
        #     'symbol': event.get('symbol'),
        #     'data': data
        # }
        # await self.send(text_data=json.dumps(message))

        # برای سادگی، فرض می‌کنیم کل محتوای event['data'] همان چیزی است که باید ارسال شود
        try:
            await self.send(text_data=json.dumps(data))
        except Exception as e:
            logger.error(f"Error sending market data to WebSocket for user {self.user.username}: {str(e)}")
            # ممکن است بخواهید اتصال را ببندید یا فقط خطا را گزارش دهید


    @database_sync_to_async
    def _validate_subscription(self, symbol: str, exchange_name: str, data_type: str) -> bool:
        """
        Validates if a subscription request is valid against the database.
        Checks if the instrument and exchange combination exists and is active.
        """
        try:
            # 1. یافتن نماد
            instrument = Instrument.objects.get(symbol__iexact=symbol)
            # 2. یافتن نگاشت صرافی
            exchange_map = InstrumentExchangeMap.objects.get(
                instrument=instrument,
                exchange__name__iexact=exchange_name, # فرض بر این است که نام صرافی در مدل Exchange ذخیره می‌شود
                is_active=True
            )
            # 3. (اختیاری) چک کردن اینکه آیا نوع داده پشتیبانی می‌شود یا خیر (مثلاً آیا صرافی کندل 1m را می‌دهد؟)
            # این ممکن است نیازمند فیلدهای بیشتری در InstrumentExchangeMap باشد.
            # برای مثال ساده، فقط وجود نگاشت فعال را چک می‌کنیم.
            return True
        except (Instrument.DoesNotExist, InstrumentExchangeMap.DoesNotExist):
            logger.warning(f"Invalid subscription request: {symbol} on {exchange_name}.")
            return False
        except Exception as e:
            logger.error(f"Error validating subscription for {symbol} on {exchange_name}: {str(e)}")
            return False

# --- مصرف‌کننده‌های دیگر (اختیاری) ---
# مثلاً یک مصرف‌کننده برای اعلان‌های مربوط به نمادها
class InstrumentNotificationConsumer(AsyncWebsocketConsumer):
    """
    Consumer for handling instrument-specific notifications (e.g., news, splits, halts).
    """
    async def connect(self):
        user = self.scope.get("user", None)
        if not (user and user.is_authenticated):
            await self.close(code=4001)
            return

        await self.accept()
        self.notifications_channel = f"instrument_notifications_{self.user.id}"
        await self.channel_layer.group_add(self.notifications_channel, self.channel_name)
        logger.info(f"Notification WebSocket connected for user {self.user.username}.")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.notifications_channel, self.channel_name)
        logger.info(f"Notification WebSocket disconnected for user {self.user.username}.")

    async def receive(self, text_data):
        # احتمالاً فقط اتصال/قطع مهم است، نه پیام‌های ورودی زیاد
        data = json.loads(text_data)
        # ... منطق دریافت (اگر نیاز باشد) ...
        pass

    async def send_notification(self, event):
        """
        Receives notification data from the channel layer and sends it to the client.
        """
        notification_data = event['data']
        await self.send(text_data=json.dumps(notification_data))

# --- مصرف‌کننده‌ای برای ارتباط با عامل‌های داده ---
# این فقط در صورتی معنادار است که عامل‌ها مستقیماً با WebSocket ارتباط داشته باشند
# که معمولاً اینطور نیست. عامل‌ها معمولاً فقط با MessageBus و پایگاه داده تعامل دارند.
# بنابراین، این بخش ممکن است کاربرد کمتری داشته باشد یا برای نظارت بر عامل‌ها استفاده شود.
# class AgentCommunicationConsumer(AsyncWebsocketConsumer):
#     # ...
#     pass
