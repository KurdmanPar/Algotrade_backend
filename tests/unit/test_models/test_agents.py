# tests/unit/test_models/test_agents.py
import pytest
from tests.factories.agents_factories import AgentFactory, AgentInstanceFactory

@pytest.mark.django_db
def test_agent_creation():
    agent = AgentFactory()
    assert agent.name is not None
    assert agent.owner is not None
    assert agent.is_active is True

@pytest.mark.django_db
def test_agent_instance_creation():
    instance = AgentInstanceFactory()
    assert instance.agent is not None
    assert instance.status == "RUNNING"