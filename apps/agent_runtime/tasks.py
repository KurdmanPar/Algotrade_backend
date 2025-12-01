# apps/agent_runtime/tasks.py
from celery import shared_task
from django.conf import settings
from .messaging import MessageBus
from .agents import BaseAgent
from apps.agents.models import Agent as AgentModel, AgentStatus

message_bus = MessageBus()

@shared_task(bind=True)
def run_agent_task(self, agent_id: int):
    """
    تسک Celery برای اجرای یک Agent.
    """
    try:
        agent_model = AgentModel.objects.get(id=agent_id)
        if not agent_model.is_active:
            raise Exception(f"Agent {agent_id} is not active.")

        # نگاشت نوع Agent به کلاس مربوطه
        agent_classes = {
            'MARKET_DATA_AGENT': 'MarketDataAgent',
            'STRATEGY_AGENT': 'StrategyAgent',
            'RISK_AGENT': 'RiskAgent',
            'EXECUTION_AGENT': 'ExecutionAgent',
            # سایر نوع‌ها...
        }
        agent_type_name = agent_model.type.name.upper().replace(" ", "_")
        agent_class_name = agent_classes.get(agent_type_name)

        if not agent_class_name:
            raise ValueError(f"Unknown agent type: {agent_model.type.name}")

        # فرض کنید کلاس‌های Agent در همین فایل یا یک ماژول مشخص هستند
        # برای سادگی، مستقیماً کلاس را اینجکت می‌کنیم
        if agent_class_name == 'MarketDataAgent':
            from .agents import MarketDataAgent
            agent_instance = MarketDataAgent(agent_model, message_bus)
        elif agent_class_name == 'StrategyAgent':
            from .agents import StrategyAgent
            agent_instance = StrategyAgent(agent_model, message_bus)
        elif agent_class_name == 'RiskAgent':
            from .agents import RiskAgent
            agent_instance = RiskAgent(agent_model, message_bus)
        elif agent_class_name == 'ExecutionAgent':
            from .agents import ExecutionAgent
            agent_instance = ExecutionAgent(agent_model, message_bus)
        else:
            raise ValueError(f"No class found for agent type: {agent_class_name}")

        agent_instance.start()

        # اینجا حلقه اصلی Agent قرار می‌گیرد (مثلاً یک حلقه بی‌نهایت یا یک consumer)
        # برای مثال ساده، فقط یک بار اجرا می‌کنیم و تسک را تمام می‌کنیم.
        # در عمل، ممکن است از یک consumer دائمی استفاده شود.

        # agent_instance.run_loop()

        agent_instance.stop()

    except AgentModel.DoesNotExist:
        raise Exception(f"Agent with id {agent_id} does not exist.")
    except Exception as e:
        # ثبت خطا در وضعیت Agent
        AgentStatus.objects.update_or_create(
            agent_id=agent_id,
            defaults={
                'state': 'ERROR',
                'last_error': str(e),
            }
        )
        raise e