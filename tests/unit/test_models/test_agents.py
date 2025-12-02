# tests/unit/test_models/test_agents.py
import pytest
from django.test import TestCase
from apps.agents.models import Agent, AgentType, AgentConfig, AgentStatus
from tests.factories import AgentFactory, AgentTypeFactory, AgentConfigFactory, AgentStatusFactory


@pytest.mark.django_db
class TestAgentModel:
    def test_agent_creation(self):
        """Test creating an agent."""
        agent = AgentFactory()
        assert agent.name is not None
        assert agent.type is not None
        assert agent.is_active is True

    def test_agent_str(self):
        """Test agent string representation."""
        agent = AgentFactory()
        assert str(agent) == f"{agent.name} ({agent.type.name})"

    def test_agent_config_creation(self):
        """Test creating an agent config."""
        config = AgentConfigFactory()
        assert config.agent is not None
        assert config.params is not None

    def test_agent_status_creation(self):
        """Test creating an agent status."""
        status = AgentStatusFactory()
        assert status.agent is not None
        assert status.state == "running"
        # حذف تست last_heartbeat چون فیلد وجود ندارد