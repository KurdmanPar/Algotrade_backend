# tests/conftest.py
import pytest
from tests.factories import *

@pytest.fixture(scope='session')
def django_db_setup():
    """Setup database for tests."""
    pass

@pytest.fixture
def user(db):
    """Create a test user."""
    return UserFactory()

@pytest.fixture
def agent_type(db):
    """Create a test agent type."""
    return AgentTypeFactory()

@pytest.fixture
def agent(db, agent_type):
    """Create a test agent."""
    return AgentFactory(type=agent_type)

@pytest.fixture
def instrument_group(db):
    """Create a test instrument group."""
    return InstrumentGroupFactory()

@pytest.fixture
def instrument(db, instrument_group):
    """Create a test instrument."""
    return InstrumentFactory(group=instrument_group)

@pytest.fixture
def indicator_group(db):
    """Create a test indicator group."""
    return IndicatorGroupFactory()

@pytest.fixture
def indicator(db, indicator_group):
    """Create a test indicator."""
    return IndicatorFactory(group=indicator_group)

@pytest.fixture
def strategy(db, user):
    """Create a test strategy."""
    return StrategyFactory(owner=user)

@pytest.fixture
def strategy_version(db, strategy):
    """Create a test strategy version."""
    return StrategyVersionFactory(strategy=strategy)