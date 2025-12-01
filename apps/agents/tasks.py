# apps/agents/tasks.py
from celery import shared_task
from .market_data_agent import MarketDataAgent
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True)
def run_market_data_agent(self, agent_model_id: int):
    """
    تسک Celery برای اجرای MarketDataAgent.
    """
    try:
        agent = MarketDataAgent(agent_model_id)
        agent.start()
    except Exception as e:
        logger.error(f"MarketDataAgent task failed: {e}")
        raise e