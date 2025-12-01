# apps/agent_runtime/agents.py
import logging
from datetime import datetime
from typing import Dict, Any
from .messaging import MessageBus
from apps.agents.models import Agent as AgentModel  # مدلی که قبلاً ساختیم

logger = logging.getLogger(__name__)

class BaseAgent:
    """
    کلاس پایه برای تمام Agentها.
    """
    def __init__(self, agent_model: AgentModel, message_bus: MessageBus):
        self.agent_model = agent_model
        self.message_bus = message_bus
        self.id = agent_model.id
        self.name = agent_model.name
        self.type = agent_model.type.name
        self.is_active = agent_model.is_active
        self.config = agent_model.config.params  # از مدل AgentConfig

    def start(self):
        """
        شروع عملیات Agent.
        """
        logger.info(f"Agent {self.name} (ID: {self.id}) started.")
        self.on_start()
        # ثبت شروع در پایگاه داده
        self.update_status("RUNNING")

    def stop(self):
        """
        توقف Agent.
        """
        logger.info(f"Agent {self.name} (ID: {self.id}) stopped.")
        self.on_stop()
        self.update_status("STOPPED")

    def pause(self):
        """
        توقف موقت Agent.
        """
        logger.info(f"Agent {self.name} (ID: {self.id}) paused.")
        self.update_status("PAUSED")

    def resume(self):
        """
        ادامه عملیات Agent.
        """
        logger.info(f"Agent {self.name} (ID: {self.id}) resumed.")
        self.update_status("RUNNING")

    def send_message(self, topic: str, payload: Dict[str, Any]):
        """
        ارسال یک پیام.
        """
        message = {
            "message_id": f"{self.id}-{datetime.utcnow().isoformat()}",
            "sender": self.name,
            "target": None,  # یا یک گیرنده مشخص
            "type": "GENERIC",
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat(),
            "correlation_id": None,  # برای ردیابی جریان
        }
        self.message_bus.publish(topic, message)
        logger.debug(f"Agent {self.name} published message to {topic}")

    def on_start(self):
        """
        متدی که هنگام شروع Agent فراخوانی می‌شود.
        قابل override توسط زیرکلاس‌ها.
        """
        pass

    def on_stop(self):
        """
        متدی که هنگام توقف Agent فراخوانی می‌شود.
        قابل override توسط زیرکلاس‌ها.
        """
        pass

    def update_status(self, status: str):
        """
        بروزرسانی وضعیت Agent در پایگاه داده.
        """
        try:
            from apps.agents.models import AgentStatus
            status_obj, created = AgentStatus.objects.update_or_create(
                agent=self.agent_model,
                defaults={
                    'state': status,
                    'last_heartbeat_at': datetime.now(),
                }
            )
        except Exception as e:
            logger.error(f"Failed to update status for agent {self.id}: {e}")


class MarketDataAgent(BaseAgent):
    """
    Agent مسئول جمع‌آوری و انتشار داده‌های بازار.
    """
    def on_start(self):
        logger.info(f"MarketDataAgent {self.name} is starting data feed...")
        # فرض کنید یک تابع `start_feed` وجود دارد که از یک کانکتور استفاده می‌کند
        # self.start_feed()

    def on_stop(self):
        logger.info(f"MarketDataAgent {self.name} is stopping data feed...")
        # self.stop_feed()


class StrategyAgent(BaseAgent):
    """
    Agent مسئول تحلیل داده و تولید سیگنال.
    """
    def on_start(self):
        logger.info(f"StrategyAgent {self.name} is subscribing to market data...")
        # مثلاً:
        # self.message_bus.subscribe("market_data.tick", self.on_market_tick)

    def on_market_tick(self, data: Dict[str, Any]):
        # منطق تحلیل و تولید سیگنال
        signal = self.analyze(data)
        if signal:
            self.send_message("signals.new", signal)

    def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # منطق تحلیل
        return {}


class RiskAgent(BaseAgent):
    """
    Agent مسئول بررسی ریسک.
    """
    def on_start(self):
        logger.info(f"RiskAgent {self.name} is listening for signals/orders...")
        # self.message_bus.subscribe("signals.new", self.on_signal)
        # self.message_bus.subscribe("orders.new", self.on_order)

    def on_signal(self, signal: Dict[str, Any]):
        # بررسی ریسک
        if self.is_risky(signal):
            self.send_message("risk.rejected", {"signal_id": signal.get("id")})
        else:
            self.send_message("risk.approved", {"signal_id": signal.get("id")})

    def is_risky(self, data: Dict[str, Any]) -> bool:
        # منطق بررسی ریسک
        return False


class ExecutionAgent(BaseAgent):
    """
    Agent مسئول اجرای سفارش.
    """
    def on_start(self):
        logger.info(f"ExecutionAgent {self.name} is ready to execute orders...")
        # self.message_bus.subscribe("orders.pending", self.on_order_pending)

    def on_order_pending(self, order: Dict[str, Any]):
        # ارسال به کانکتور صرافی
        # result = self.execute_order(order)
        # self.send_message("orders.executed", result)
        pass