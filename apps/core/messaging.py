# apps/core/messaging.py

import json
import logging
from typing import Dict, Any, Optional, Callable, List
from django.conf import settings
from django.utils import timezone
from .exceptions import CoreSystemException, MessagingError # فرض بر این است که این استثناها وجود دارند
from .models import AuditLog # فرض بر این است که مدل AuditLog وجود دارد

logger = logging.getLogger(__name__)

# --- استثناهای مرتبط با پیام‌رسانی ---
class MessagingError(CoreSystemException):
    """
    Base exception for errors occurring within the messaging system.
    """
    status_code = 500
    default_detail = _('An error occurred in the messaging system.')
    default_code = 'messaging_error'

class MessageSendError(MessagingError):
    """
    Raised when an error occurs while sending a message.
    """
    status_code = 500
    default_detail = _('Failed to send message.')
    default_code = 'message_send_error'

class MessageReceiveError(MessagingError):
    """
    Raised when an error occurs while receiving a message.
    """
    status_code = 500
    default_detail = _('Failed to receive message.')
    default_code = 'message_receive_error'

class MessageParseError(MessagingError):
    """
    Raised when a received message cannot be parsed.
    """
    status_code = 400
    default_detail = _('Failed to parse received message.')
    default_code = 'message_parse_error'

# --- ابزار اصلی: MessageBus ---
class MessageBus:
    """
    Central hub for inter-agent communication within the MAS.
    This class provides a unified interface for publishing and subscribing to messages/events.
    It abstracts the underlying message broker (e.g., Redis, RabbitMQ, Celery).
    """
    def __init__(self, broker_type: str = 'redis'):
        """
        Initializes the MessageBus with a specific broker.
        Args:
            broker_type: The type of broker to use ('redis', 'rabbitmq', 'celery', 'memory').
        """
        self.broker_type = broker_type
        self._broker_instance = self._initialize_broker()
        logger.info(f"MessageBus initialized with broker type: {broker_type}")

    def _initialize_broker(self):
        """
        Initializes the specific broker instance based on the broker_type.
        """
        if self.broker_type == 'redis':
            try:
                import redis
                redis_host = getattr(settings, 'REDIS_HOST', 'localhost')
                redis_port = getattr(settings, 'REDIS_PORT', 6379)
                redis_db = getattr(settings, 'REDIS_DB', 0)
                r = redis.Redis(host=redis_host, port=redis_port, db=redis_db, decode_responses=True)
                return r
            except ImportError:
                logger.error("Redis library not installed. Install 'redis' package.")
                raise MessagingError("Redis library not found.")
        elif self.broker_type == 'rabbitmq':
            # مثال: استفاده از pika
            # try:
            #     import pika
            #     connection_params = pika.ConnectionParameters(host=settings.RABBITMQ_HOST)
            #     connection = pika.BlockingConnection(connection_params)
            #     channel = connection.channel()
            #     return channel
            # except ImportError:
            #     logger.error("Pika library not installed. Install 'pika' package.")
            #     raise MessagingError("Pika library not found.")
            logger.warning("RabbitMQ broker initialization is not fully implemented in this example.")
            return None # یا ایجاد یک استثنا
        elif self.broker_type == 'celery':
            # مثال: استفاده از Celery Tasks به عنوان مکانیزم پیام‌رسانی
            # می‌توانید یک تاسک ساده برای ارسال پیام تعریف کنید و از `delay` یا `apply_async` استفاده کنید
            # from .tasks import dispatch_message_task
            # self._dispatch_task = dispatch_message_task.delay
            logger.warning("Celery broker implementation as a message bus is not fully shown here. Typically, dedicated tasks are used.")
            return None # یا ارجاع به یک تابع/تاسک Celery
        elif self.broker_type == 'memory': # برای تست یا توسعه
            import threading
            self._in_memory_queue = {}
            self._locks = {}
            return self._in_memory_queue
        else:
            raise MessagingError(f"Unsupported broker type: {self.broker_type}")

    def publish(self, topic: str, message_ Dict[str, Any], sender_id: Optional[str] = None):
        """
        Publishes a message to a specific topic/channel.
        Args:
            topic: The topic to publish the message to.
            message_: The message payload (dictionary).
            sender_id: Optional ID of the agent sending the message.
        """
        try:
            envelope = {
                'topic': topic,
                'message': message_,
                'sender_id': sender_id,
                'timestamp': timezone.now().isoformat(),
                'correlation_id': message_.get('correlation_id', None) # برای ردیابی درخواست/پاسخ
            }
            serialized_envelope = json.dumps(envelope)

            if self.broker_type == 'redis':
                self._broker_instance.publish(topic, serialized_envelope)
                logger.debug(f"Message published to Redis topic '{topic}' by sender '{sender_id}'.")
            elif self.broker_type == 'rabbitmq':
                 # مثال برای RabbitMQ
                 # self._broker_instance.basic_publish(exchange='', routing_key=topic, body=serialized_envelope)
                 # logger.debug(f"Message published to RabbitMQ queue '{topic}' by sender '{sender_id}'.")
                 pass # پیاده‌سازی RabbitMQ
            elif self.broker_type == 'memory':
                # ارسال پیام به صف حافظه (ساده‌شده)
                if topic not in self._broker_instance:
                    self._broker_instance[topic] = []
                self._broker_instance[topic].append(serialized_envelope)
                logger.debug(f"Message published to in-memory topic '{topic}' by sender '{sender_id}'.")
            # ... سایر بروکرها

            # ثبت در حسابرسی (اختیاری)
            # AuditLog.objects.create(
            #     user=None, # ممکن است نیاز به تعریف کاربر مجازی یا نمایندگی عامل باشد
            #     action='MESSAGE_PUBLISHED',
            #     target_model='MessageBus',
            #     target_id=None,
            #     details={'topic': topic, 'sender_id': sender_id},
            #     ip_address='N/A', # یا IP عامل
            #     user_agent='MAS_Agent',
            # )

        except Exception as e:
            logger.error(f"Error publishing message to topic '{topic}': {str(e)}")
            raise MessageSendError(f"Failed to publish message to topic '{topic}': {str(e)}")

    def subscribe(self, topic: str, handler: Callable[[Dict[str, Any]], None]):
        """
        Subscribes a handler function to a specific topic.
        The handler will be called when a message arrives on the topic.
        This is a simplified example, often requiring async processing (e.g., using asyncio or threads).
        Args:
            topic: The topic to subscribe to.
            handler: The function to call when a message is received.
        """
        if self.broker_type == 'redis':
            try:
                import redis
                pubsub = self._broker_instance.pubsub()
                pubsub.subscribe(topic)

                logger.info(f"Subscribed to Redis topic '{topic}'.")

                for message in pubsub.listen():
                    if message['type'] == 'message':
                        try:
                            envelope_str = message['data']
                            envelope = json.loads(envelope_str)
                            deserialized_message = envelope['message']
                            sender_id = envelope.get('sender_id')
                            logger.debug(f"Message received from topic '{topic}' by handler (sender: {sender_id}).")
                            handler(deserialized_message)
                        except json.JSONDecodeError as je:
                            logger.error(f"Failed to parse message from topic '{topic}': {str(je)}")
                            raise MessageParseError(f"Failed to parse message from topic '{topic}': {str(je)}")
                        except Exception as e:
                            logger.error(f"Error processing message from topic '{topic}': {str(e)}")
                            # ممکن است بخواهید خطایی را گزارش دهید یا دوباره بالا بیاورید
                            # raise MessageReceiveError(f"Error in handler for topic '{topic}': {str(e)}")
            except Exception as e:
                logger.error(f"Error in Redis subscription for topic '{topic}': {str(e)}")
                raise MessageReceiveError(f"Failed to subscribe or receive from topic '{topic}': {str(e)}")

        elif self.broker_type == 'memory':
            # ساده‌ترین پیاده‌سازی برای تست: گوش دادن به یک صف حافظه
            # این فقط یک مثال است و برای محصول نباید استفاده شود
            import time
            while True:
                if topic in self._broker_instance and self._broker_instance[topic]:
                    msg_str = self._broker_instance[topic].pop(0) # FIFO
                    try:
                        envelope = json.loads(msg_str)
                        deserialized_message = envelope['message']
                        sender_id = envelope.get('sender_id')
                        logger.debug(f"Message received from in-memory topic '{topic}' by handler (sender: {sender_id}).")
                        handler(deserialized_message)
                    except json.JSONDecodeError as je:
                        logger.error(f"Failed to parse message from in-memory topic '{topic}': {str(je)}")
                        raise MessageParseError(f"Failed to parse message from in-memory topic '{topic}': {str(je)}")
                    except Exception as e:
                        logger.error(f"Error processing message from in-memory topic '{topic}': {str(e)}")
                        # raise MessageReceiveError(f"Error in handler for in-memory topic '{topic}': {str(e)}")
                time.sleep(0.1) # polling delay
        # ... سایر بروکرها (مثل RabbitMQ)

    def broadcast(self, message_ Dict[str, Any], sender_id: Optional[str] = None, exclude_senders: Optional[List[str]] = None):
        """
        Broadcasts a message to all connected agents.
        This might be implemented by sending to a special 'broadcast' topic
        or by iterating through known subscribers (more complex).
        For this example, we'll publish to a 'broadcast' topic.
        """
        if exclude_senders is None:
            exclude_senders = []
        # اگر sender_id در لیست استثناها بود، ارسال نکن
        if sender_id in exclude_senders:
             logger.debug(f"Broadcast skipped for sender {sender_id} as it's in the exclusion list.")
             return

        self.publish('broadcast', message_, sender_id)


# --- کلاس پایه برای عامل‌ها ---
class BaseAgent:
    """
    Base class for agents in the MAS.
    Provides common methods for sending/receiving messages via the MessageBus.
    """
    def __init__(self, agent_config: Dict[str, Any], message_bus: MessageBus):
        self.agent_config = agent_config
        self.message_bus = message_bus
        self.agent_id = agent_config.get('id', 'generic_agent')
        self.subscribed_topics = set()

    def send_message(self, topic: str, message_ Dict[str, Any]):
        """
        Sends a message via the message bus.
        """
        try:
            self.message_bus.publish(topic, message, sender_id=self.agent_id)
        except MessagingError as e:
            logger.error(f"Agent {self.agent_id} failed to send message: {str(e)}")
            # منطق مدیریت خطا مانند تلاش مجدد
            raise

    def broadcast_message(self, message_ Dict[str, Any], exclude_self: bool = True):
        """
        Broadcasts a message to all agents.
        """
        exclude_list = [self.agent_id] if exclude_self else []
        self.message_bus.broadcast(message, sender_id=self.agent_id, exclude_senders=exclude_list)

    def subscribe_to_topic(self, topic: str, handler: Callable[[Dict[str, Any]], None]):
        """
        Subscribes the agent to a specific topic.
        """
        # ممکن است نیاز به ذخیره handler در یک لیست داخلی داشته باشیم برای مدیریت اشتراک
        # یا اینکه فقط به MessageBus دستور دهیم که اشتراک را مدیریت کند
        # در این مثال، فقط MessageBus اشتراک را مدیریت می‌کند
        self.subscribed_topics.add(topic)
        self.message_bus.subscribe(topic, handler)

    def start_listening(self):
        """
        Starts the agent's listening loop (often implemented asynchronously).
        This is a placeholder; actual implementation depends heavily on the broker.
        """
        logger.info(f"Agent {self.agent_id} started listening on topics: {self.subscribed_topics}")
        # در عمل، این ممکن است یک حلقه asyncio یا یک ترد باشد که منتظر پیام است
        # self.message_bus.subscribe_multiple(topics=self.subscribed_topics, handler=self._handle_message)

    def _handle_message(self, message_ Dict[str, Any]):
        """
        Internal handler to process incoming messages based on their type.
        This method should be overridden by subclasses.
        """
        msg_type = message.get('type')
        if msg_type == 'ORDER_SIGNAL':
            self._on_order_signal(message)
        elif msg_type == 'MARKET_DATA_UPDATE':
            self._on_market_data_update(message)
        elif msg_type == 'RISK_ALERT':
            self._on_risk_alert(message)
        # ... سایر انواع پیام
        else:
            logger.warning(f"Agent {self.agent_id} received unknown message type: {msg_type}")

    # متدهای خالی برای override شدن توسط زیرکلاس‌ها
    def _on_order_signal(self, message_ Dict[str, Any]): pass
    def _on_market_data_update(self, message_ Dict[str, Any]): pass
    def _on_risk_alert(self, message_ Dict[str, Any]): pass
    # ... سایر متد هندلرها ...

# --- ابزارهای کمکی ---
def create_correlation_id() -> str:
    """
    Creates a unique correlation ID for tracking related messages/requests.
    """
    import uuid
    return str(uuid.uuid4())

# --- نمونه استفاده ---
# message_bus = MessageBus(broker_type='redis')
# agent1 = BaseAgent({'id': 'data_collector_1'}, message_bus)
# agent2 = BaseAgent({'id': 'trading_bot_1'}, message_bus)
#
# def handle_order_signal(msg):
#     print(f"Trading Bot received signal: {msg}")
#
# agent2.subscribe_to_topic('signals.trading', handle_order_signal)
# agent1.send_message('signals.trading', {'type': 'ORDER_SIGNAL', 'symbol': 'BTCUSDT', 'side': 'BUY', 'price': 50000})
#
# # شروع گوش دادن (در یک ترد یا asyncio)
# # agent2.start_listening() # این ممکن است نیاز به asyncio یا threading داشته باشد

logger.info("Messaging system components loaded.")
