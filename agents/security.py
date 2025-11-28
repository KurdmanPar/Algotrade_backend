# agents/security.py
import jwt
import logging
from datetime import datetime, timedelta
from django.conf import settings
from .models import Agent

logger = logging.getLogger(__name__)


class AgentAuth:
    """سیستم احراز هویت برای عامل‌ها"""

    @staticmethod
    def generate_token(agent: Agent) -> str:
        """生成令牌用于代理身份验证"""
        payload = {
            'agent_id': agent.id,
            'agent_name': agent.name,
            'exp': datetime.utcnow() + timedelta(hours=24),
            'iat': datetime.utcnow()
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

    @staticmethod
    def verify_token(token: str) -> Optional[Agent]:
        """验证代理令牌并返回代理对象"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
            agent_id = payload.get('agent_id')
            return Agent.objects.get(id=agent_id)
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, Agent.DoesNotExist):
            return None


# agents/logging.py
import logging
from django.conf import settings
from .models import Agent, AgentMessage


class AgentLogger:
    """سیستم لاگ‌گیری برای فعالیت‌های عامل‌ها"""

    def __init__(self, agent: Agent):
        self.agent = agent
        self.logger = logging.getLogger(f"agent.{agent.name}")

        # تنظیم لاگر برای نوشتن در فایل و دیتابیس
        if not self.logger.handlers:
            file_handler = logging.FileHandler(settings.AGENT_LOG_FILE)
            file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
            self.logger.addHandler(file_handler)

            # تعریف یک لاگر سفارشی برای ذخیره در دیتابیس
            db_handler = DatabaseLogHandler(agent)
            self.logger.addHandler(db_handler)

    def log_message(self, level: str, message: str, extra_data: dict = None):
        """ثبت لاگ با سطح مشخص"""
        log_method = getattr(self.logger, level.lower(), self.logger.info)
        log_method(message, extra={'extra_data': extra_data or {}})

    def log_incoming_message(self, message: AgentMessage):
        """ثبت پیام دریافتی"""
        self.log_message(
            "info",
            f"Received message from {message.sender.name}: {message.message_type}",
            {
                "message_id": message.id,
                "sender": message.sender.name,
                "message_type": message.message_type,
                "payload": message.payload
            }
        )

    def log_outgoing_message(self, message: AgentMessage):
        """ثبت پیام ارسالی"""
        self.log_message(
            "info",
            f"Sent message to {message.receiver.name}: {message.message_type}",
            {
                "message_id": message.id,
                "receiver": message.receiver.name,
                "message_type": message.message_type,
                "payload": message.payload
            }
        )


class DatabaseLogHandler(logging.Handler):
    """لاگر سفارشی برای ذخیره لاگ‌ها در دیتابیس"""

    def __init__(self, agent: Agent):
        super().__init__()
        self.agent = agent

    def emit(self, record):
        """ذخیره لاگ در دیتابیس"""
        from .models import AgentLog

        extra_data = getattr(record, 'extra_data', {})

        AgentLog.objects.create(
            agent=self.agent,
            level=record.levelname,
            message=record.getMessage(),
            extra_data=extra_data,
            timestamp=record.created
        )