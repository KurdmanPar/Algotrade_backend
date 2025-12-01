# apps/agent_runtime/messaging.py
import json
import redis
from django.conf import settings
from typing import Dict, Any, Callable

# تنظیمات Redis از settings
REDIS_HOST = getattr(settings, 'REDIS_HOST', 'localhost')
REDIS_PORT = getattr(settings, 'REDIS_PORT', 6379)
REDIS_DB = getattr(settings, 'REDIS_DB', 0)

r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

class MessageBus:
    """
    لایه انتزاعی برای ارسال و دریافت پیام بین عامل‌ها.
    """
    def publish(self, topic: str, message: Dict[str, Any]):
        """
        انتشار یک پیام در یک موضوع (topic).
        """
        r.publish(topic, json.dumps(message))

    def subscribe(self, topic: str, callback: Callable[[Dict[str, Any]], None]):
        """
        اشتراک در یک موضوع و فراخوانی یک تابع هنگام دریافت پیام.
        این تابع باید در یک فرآیند جداگانه یا ترد اجرا شود.
        """
        pubsub = r.pubsub()
        pubsub.subscribe(topic)

        for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                callback(data)