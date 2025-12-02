# tests/factories.py
import factory
from django.contrib.auth import get_user_model
from apps.agents.models import Agent, AgentType, AgentConfig, AgentStatus
from apps.instruments.models import Instrument, InstrumentGroup, Indicator, IndicatorGroup
from apps.strategies.models import Strategy, StrategyVersion

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Faker('email')
    username = factory.Faker('user_name')
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True


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
    last_heartbeat = factory.Faker('date_time_this_year')
    last_error = ""


class InstrumentGroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InstrumentGroup

    name = factory.Sequence(lambda n: f"Group {n}")
    description = factory.Faker('text')


class InstrumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Instrument

    symbol = factory.Sequence(lambda n: f"SYMBOL{n}")
    name = factory.Faker('company')
    group = factory.SubFactory(InstrumentGroupFactory)
    base_asset = "BTC"
    quote_asset = "USDT"
    tick_size = 0.01
    lot_size = 0.001
    is_active = True


class IndicatorGroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = IndicatorGroup

    name = factory.Sequence(lambda n: f"IndicatorGroup {n}")
    description = factory.Faker('text')


class IndicatorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Indicator

    name = factory.Sequence(lambda n: f"Indicator {n}")
    code = factory.Sequence(lambda n: f"INDICATOR_{n}")
    group = factory.SubFactory(IndicatorGroupFactory)
    description = factory.Faker('text')


class StrategyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Strategy

    owner = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"Strategy {n}")
    description = factory.Faker('text')
    category = "FULL"
    is_active = True


class StrategyVersionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StrategyVersion

    strategy = factory.SubFactory(StrategyFactory)
    version = factory.Sequence(lambda n: f"1.{n}.0")
    parameters_schema = factory.lazy_attribute(lambda _: {
        "param1": {"type": "integer", "default": 10},
        "param2": {"type": "float", "default": 0.5}
    })
    indicator_configs = factory.lazy_attribute(lambda _: [
        {"indicator": "RSI", "params": {"period": 14}},
        {"indicator": "MACD", "params": {"fast": 12, "slow": 26, "signal": 9}}
    ])
    price_action_configs = factory.lazy_attribute(lambda _: [])
    smart_money_configs = factory.lazy_attribute(lambda _: [])
    ai_metrics_configs = factory.lazy_attribute(lambda _: [])
    is_approved_for_live = False

