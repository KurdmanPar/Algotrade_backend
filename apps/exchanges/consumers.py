# apps/exchanges/consumers.py

from channels.generic.websocket import AsyncWebsocketConsumer
from apps.core.consumers import SecureWebSocketConsumer # import از core
from apps.exchanges.models import ExchangeAccount, OrderHistory
from apps.core.services import AuditService # import از core
import json
import logging

logger = logging.getLogger(__name__)

# --- Consumer برای وضعیت حساب صرافی ---
class ExchangeAccountStatusConsumer(SecureWebSocketConsumer):
    """
    Consumer for real-time updates on exchange account status (e.g., balance changes, order fills).
    Inherits security checks from core.
    """
    async def connect(self):
        # احراز هویت و چک کردن مالکیت در SecureWebSocketConsumer انجام می‌شود
        await super().connect() # فراخوانی connect والد
        # اتصال معمولاً به یک چنل خاص مربوط به حساب کاربر است
        # self.account_id = self.scope['url_route']['kwargs']['account_id']
        # self.room_group_name = f'account_status_{self.account_id}'
        # await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        # logger.info(f"WebSocket connected for account status updates by user {self.user.email}.")

    async def disconnect(self, close_code):
        await super().disconnect(close_code)
        # await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        logger.info(f"WebSocket disconnected for account status updates by user {self.user.email}.")

    # متدی برای دریافت پیام از کلاینت (مثلاً درخواست اشتراک)
    async def receive(self, text_data=None, bytes_data=None):
        await super().receive(text_data, bytes_data) # فراخوانی receive والد

    # متدی برای دریافت پیام از چنل (مثلاً از طریق یک سرویس/تاسک/سیگنال)
    async def account_status_update(self, event):
        """
        Handles account status update messages sent via channel_layer.
        e.g., balance change, new order, order fill.
        """
        # گرفتن داده از رویداد
        data = event['data']

        # ارسال داده به کلاینت
        await self.send(text_data=json.dumps(data))


# --- Consumer برای تاریخچه سفارشات ---
class OrderHistoryConsumer(SecureWebSocketConsumer):
    """
    Consumer for real-time order history updates.
    """
    async def connect(self):
        await super().connect()
        # ممکن است کاربر به چنلی مربوط به سفارشات خود متصل شود
        # self.user_id = self.scope['user'].id
        # self.room_group_name = f'user_orders_{self.user_id}'
        # await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        # logger.info(f"WebSocket connected for order history updates by user {self.user.email}.")

    async def disconnect(self, close_code):
        await super().disconnect(close_code)
        # await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        logger.info(f"WebSocket disconnected for order history updates by user {self.user.email}.")

    async def receive(self, text_data=None, bytes_data=None):
        await super().receive(text_data, bytes_data)

    async def order_update(self, event):
        """
        Handles order update messages sent via channel_layer.
        """
        data = event['data']
        await self.send(text_data=json.dumps(data))


# --- Consumer برای اعلان‌های صرافی ---
class ExchangeNotificationConsumer(SecureWebSocketConsumer):
    """
    Consumer for general exchange notifications (e.g., maintenance alerts, new features).
    """
    async def connect(self):
        await super().connect()
        # کاربر ممکن است به یک چنل عمومی یا چنل‌های خاصی مانند صرافی‌هایی که حساب دارد، متصل شود
        # self.user_exchanges = self.user.exchange_accounts.values_list('exchange__code', flat=True)
        # for ex_code in self.user_exchanges:
        #     await self.channel_layer.group_add(f'exchange_notifications_{ex_code}', self.channel_name)
        # logger.info(f"WebSocket connected for exchange notifications by user {self.user.email}.")

    async def disconnect(self, close_code):
        await super().disconnect(close_code)
        # حذف از چنل‌های مربوطه
        # for ex_code in self.user_exchanges:
        #     await self.channel_layer.group_discard(f'exchange_notifications_{ex_code}', self.channel_name)
        logger.info(f"WebSocket disconnected for exchange notifications by user {self.user.email}.")

    async def receive(self, text_data=None, bytes_data=None):
        await super().receive(text_data, bytes_data)

    async def exchange_notification(self, event):
        """
        Handles general exchange notification messages.
        """
        data = event['data']
        await self.send(text_data=json.dumps(data))

# --- Consumer برای ارتباط با عامل‌های MAS ---
class AgentCommunicationConsumer(SecureWebSocketConsumer):
    """
    Consumer for communication between MAS agents and the system.
    """
    async def connect(self):
        # ممکن است نیاز به احراز هویت عامل (Agent) نیز داشته باشیم، نه فقط کاربر
        # این نیازمند پیاده‌سازی متفاوتی در میان‌افزار یا Consumer است
        # فرض: احراز هویت کاربر (که ممکن است یک عامل باشد یا یک کاربر ادمین) از طریق Token یا سایر روش‌ها انجام شده است
        await super().connect()
        # ممکن است چنل مربوط به ID عامل باشد
        # self.agent_id = self.scope['user'].agent_id # فرض: فیلد agent_id در مدل کاربر یا یک مدل عامل وجود دارد
        # self.room_group_name = f'agent_comm_{self.agent_id}'
        # await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        logger.info(f"WebSocket connected for agent communication by user {self.user.email}.")

    async def disconnect(self, close_code):
        await super().disconnect(close_code)
        logger.info(f"WebSocket disconnected for agent communication by user {self.user.email}.")

    async def receive(self, text_data=None, bytes_data=None):
        await super().receive(text_data, bytes_data)

    async def agent_message(self, event):
        """
        Handles messages from or to agents.
        """
        data = event['data']
        await self.send(text_data=json.dumps(data))

# --- Consumer برای داده‌های بلادرنگ صرافی ---
# توجه: معمولاً این نوع Consumerها بیشتر در اپلیکیشن `market_data` قرار می‌گیرند،
# زیرا داده‌های بلادرنگ بازار (OHLCV، OrderBook، Trades) بیشتر مربوط به آن دامنه است.
# اما اگر فقط داده‌های مربوط به یک حساب خاص (مثل balance updates) نیاز باشد، می‌تواند در `exchanges` باشد.
# اگر کامل‌تر باشد، باید در `market_data` قرار گیرد.
# class ExchangeMarketDataConsumer(SecureWebSocketConsumer):
#     ...

logger.info("Exchanges consumers loaded successfully.")
