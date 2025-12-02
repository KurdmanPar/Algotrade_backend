# tests/factories/agents.py
import factory
from apps.agents.models import Agent, AgentType, AgentConfig, AgentStatus


class AgentTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AgentType

    name = factory.Sequence(lambda n: f"AgentType {n}")
    description = factory.Faker('text')
    capabilities = factory.lazy_attribute(lambda _: {
        "consumes": ["MARKET_TICK"],
        "produces": ["SIGNAL"]
    })


class AgentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Agent

    name = factory.Sequence(lambda n: f"Agent {n}")
    type = factory.SubFactory(AgentTypeFactory)
    is_active = True


class AgentConfigFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AgentConfig

    agent = factory.SubFactory(AgentFactory)
    params = factory.lazy_attribute(lambda _: {
        "param1": "value1",
        "param2": "value2"
    })


class AgentStatusFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AgentStatus

    agent = factory.SubFactory(AgentFactory)
    state = "running"
    # حذف فیلد last_heartbeat که در مدل وجود ندارد
    last_error = ""