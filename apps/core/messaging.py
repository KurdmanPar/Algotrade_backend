# apps/core/messaging.py
import json
import asyncio
import redis.asyncio as redis
from django.conf import settings
from typing import Dict, Any, Callable

REDIS_HOST = getattr(settings, 'REDIS_HOST', 'localhost')
REDIS_PORT = getattr(settings, 'REDIS_PORT', 6379)
REDIS_DB = getattr(settings, 'REDIS_DB', 0)

class MessageBus:
    def __init__(self):
        self.redis = None

    async def connect(self):
        self.redis = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

    async def publish(self, topic: str, message: Dict[str, Any]):
        if not self.redis:
            await self.connect()
        await self.redis.publish(topic, json.dumps(message))

    async def subscribe(self, topic: str, handler: Callable[[Dict[str, Any]], None]):
        if not self.redis:
            await self.connect()
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(topic)
        async for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'])
                handler(data)