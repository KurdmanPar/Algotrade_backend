# agents/messaging.py
import json
import uuid
from typing import Dict, Any, Optional
import redis
from django.conf import settings
from .models import Agent, AgentMessage


class MessageBus:
    """سیستم پیام‌رسان بین عامل‌ها"""

    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB
        )

    def publish(self, sender: Agent, receiver: Agent, message_type: str, payload: Dict[str, Any],
                correlation_id: Optional[str] = None) -> str:
        """ارسال پیام از یک عامل به عامل دیگر"""
        message_id = str(uuid.uuid4())
        correlation_id = correlation_id or str(uuid.uuid4())

        # ذخیره پیام در دیتابیس برای لاگ و ردیابی
        AgentMessage.objects.create(
            sender=sender,
            receiver=receiver,
            message_type=message_type,
            payload=payload,
            correlation_id=correlation_id
        )

        # ارسال پیام به Redis
        message_data = {
            "message_id": message_id,
            "sender_id": sender.id,
            "receiver_id": receiver.id,
            "message_type": message_type,
            "payload": payload,
            "correlation_id": correlation_id
        }

        channel = f"agent:{receiver.id}"
        self.redis_client.publish(channel, json.dumps(message_data))

        return message_id

    def subscribe(self, agent: Agent, callback):
        """اشتراک عامل برای دریافت پیام‌ها"""
        channel = f"agent:{agent.id}"
        pubsub = self.redis_client.pubsub()
        pubsub.subscribe(channel)

        for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                # علامت‌گذاری پیام به عنوان پردازش شده
                AgentMessage.objects.filter(
                    sender_id=data["sender_id"],
                    receiver_id=data["receiver_id"],
                    correlation_id=data["correlation_id"]
                ).update(processed=True)

                # فراخوانی تابع پردازش پیام
                callback(data)