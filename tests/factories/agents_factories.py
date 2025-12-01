# tests/factories/agents_factories.py
import factory
from apps.agents.models import (
    AgentType, Agent, AgentInstance, AgentConfig, AgentStatus, AgentMessage, AgentLog, AgentMetric
)
from tests.factories.accounts_factories import UserFactory


class AgentTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AgentType

    name = factory.Sequence(lambda n: f"AgentType {n}")
    description = factory.Faker("sentence")
    capabilities = factory.Dict({
        "consumes": ["MARKET_DATA"],
        "produces": ["SIGNAL"],
        "supports_exchanges": ["BINANCE", "NOBITEX"]
    })


class AgentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Agent

    owner = factory.SubFactory(UserFactory)
    type = factory.SubFactory(AgentTypeFactory)
    name = factory.Sequence(lambda n: f"Agent {n}")
    description = factory.Faker("sentence")
    is_active = factory.Faker("boolean")
    is_paused_by_system = factory.Faker("boolean")
    last_activity_at = factory.Faker("date_time_this_month", tzinfo=None)


class AgentInstanceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AgentInstance

    agent = factory.SubFactory(AgentFactory)
    instance_id = factory.Sequence(lambda n: f"instance-{n}")
    status = factory.Iterator(["RUNNING", "PAUSED", "STOPPED", "FAILED"])
    host = factory.Faker("hostname")
    process_id = factory.Faker("pyint", min_value=1000, max_value=99999)
    started_at = factory.Faker("date_time_this_month", tzinfo=None)
    stopped_at = factory.Faker("date_time_between", start_date="+1d", end_date="+30d", tzinfo=None)


class AgentConfigFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AgentConfig

    agent = factory.SubFactory(AgentFactory)
    version = factory.Faker("numerify", text="1.0.#")
    params = factory.Dict({"param1": "value1"})
    is_active = factory.Faker("boolean")
    validation_result = factory.Dict({"valid": True, "errors": []})


class AgentStatusFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AgentStatus

    agent = factory.SubFactory(AgentFactory)
    state = factory.Iterator(["IDLE", "RUNNING", "PAUSED", "ERROR", "STOPPED"])
    last_heartbeat_at = factory.Faker("date_time_this_month", tzinfo=None)
    last_error = factory.Faker("sentence")
    metrics = factory.Dict({"cpu": 20.5, "memory_mb": 1024})
    agent_version = factory.Faker("numerify", text="1.0.#")
    process_id = factory.Faker("pyint", min_value=1000, max_value=99999)


class AgentMessageFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AgentMessage

    sender = factory.SubFactory(AgentFactory)
    sender_type = factory.SubFactory(AgentTypeFactory)
    receiver = factory.SubFactory(AgentFactory)
    receiver_type = factory.SubFactory(AgentTypeFactory)
    message_type = factory.Faker("word")
    topic = factory.Faker("slug")
    payload = factory.Dict({"data": "sample"})
    priority = factory.Iterator([1, 2, 3, 4])
    expires_at = factory.Faker("date_time_between", start_date="+1d", end_date="+7d", tzinfo=None)
    is_encrypted = factory.Faker("boolean")
    correlation_id = factory.Faker("uuid4", cast_to=str)
    retry_count = factory.Faker("pyint", min_value=0, max_value=5)
    processed = factory.Faker("boolean")


class AgentLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AgentLog

    agent = factory.SubFactory(AgentFactory)
    level = factory.Iterator(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
    message = factory.Faker("sentence")
    extra_data = factory.Dict({"extra": "info"})
    trace_id = factory.Faker("uuid4", cast_to=str)
    user_context = factory.SubFactory(UserFactory)
    resource_usage_snapshot = factory.Dict({"cpu": 20.5, "memory_mb": 1024})
    agent_instance_id = factory.Faker("uuid4", cast_to=str)


class AgentMetricFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AgentMetric

    agent = factory.SubFactory(AgentFactory)
    period_start = factory.Faker("date_time_this_month", tzinfo=None)
    period_end = factory.LazyAttribute(lambda obj: obj.period_start + factory.Faker("timedelta", minutes=1))

    cpu_usage_avg = factory.Faker("pydecimal", max_digits=5, decimal_places=2, positive=True)
    memory_usage_avg_mb = factory.Faker("pydecimal", max_digits=10, decimal_places=2, positive=True)
    disk_usage_avg_mb = factory.Faker("pydecimal", max_digits=10, decimal_places=2, positive=True)
    network_io_avg_kb = factory.Faker("pydecimal", max_digits=12, decimal_places=2, positive=True)

    messages_sent = factory.Faker("pyint", min_value=0)
    messages_received = factory.Faker("pyint", min_value=0)
    errors_count = factory.Faker("pyint", min_value=0)
    avg_processing_time_ms = factory.Faker("pydecimal", max_digits=10, decimal_places=3, positive=True)