# tests/unit/test_models/test_strategies.py
import pytest
from tests.factories.strategies_factories import StrategyFactory, StrategyVersionFactory
from tests.factories.bots_factories import BotFactory

@pytest.mark.django_db
def test_strategy_assignment_creation():
    bot = BotFactory()
    strategy_version = StrategyVersionFactory()
    assignment = StrategyAssignmentFactory(bot=bot, strategy_version=strategy_version)
    assert assignment.bot == bot
    assert assignment.strategy_version == strategy_version