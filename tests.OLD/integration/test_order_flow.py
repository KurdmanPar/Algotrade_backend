# tests/integration/test_order_flow.py
import pytest
from django.test import TestCase
from apps.agents.models import Agent, AgentType
from apps.strategies.models import Strategy, StrategyVersion
from apps.signals.models import Signal
from tests.factories import (
    AgentFactory, AgentTypeFactory, StrategyFactory,
    StrategyVersionFactory, InstrumentFactory
)


@pytest.mark.django_db
class TestOrderFlow:
    def test_signal_to_order_flow(self):
        """Test of flow from signal to order."""
        # Create test data
        agent_type = AgentTypeFactory()
        agent = AgentFactory(type=agent_type)
        strategy = StrategyFactory()
        strategy_version = StrategyVersionFactory(strategy=strategy)
        instrument = InstrumentFactory()

        # Create a signal with quantity (اصلاح شده)
        signal = Signal.objects.create(
            strategy_version=strategy_version,
            agent=agent,
            instrument=instrument,
            direction="BUY",
            signal_type="ENTRY",
            confidence_score=0.8,
            quantity=1.0,  # اضافه کردن مقدار quantity
            payload={}
        )

        # Verify signal creation
        assert signal.id is not None
        assert signal.strategy_version == strategy_version
        assert signal.agent == agent
        assert signal.instrument == instrument
        assert signal.direction == "BUY"
        assert signal.signal_type == "ENTRY"
        assert signal.confidence_score == 0.8
        assert signal.quantity == 1.0  # بررسی مقدار quantity