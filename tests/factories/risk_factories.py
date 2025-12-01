# tests/factories/risk_factories.py
import factory
from apps.risk.models import RiskProfile, RiskRule, RiskEvent, RiskMetric, RiskAlert
from tests.factories.accounts_factories import UserFactory
from tests.factories.bots_factories import BotFactory
from tests.factories.trading_factories import OrderFactory, PositionFactory
from tests.factories.signals_factories import SignalFactory
from tests.factories.strategies_factories import StrategyVersionFactory
from tests.factories.agents_factories import AgentFactory


class RiskProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RiskProfile

    owner = factory.SubFactory(UserFactory)
    bot = factory.SubFactory(BotFactory)
    name = factory.Sequence(lambda n: f"Risk Profile {n}")
    description = factory.Faker("sentence")
    risk_model_type = factory.Iterator(["CLASSIC", "AI", "RAG"])
    risk_agent = factory.SubFactory(AgentFactory)
    max_daily_loss_percent = factory.Faker("pydecimal", left_digits=4, right_digits=2, positive=True)
    max_drawdown_percent = factory.Faker("pydecimal", left_digits=4, right_digits=2, positive=True)
    max_position_size_percent = factory.Faker("pydecimal", left_digits=4, right_digits=2, positive=True)
    max_capital = factory.Faker("pydecimal", left_digits=12, right_digits=8, positive=True)
    max_positions = factory.Faker("pyint", min_value=1, max_value=100)
    max_exposure_per_instrument = factory.Faker("pydecimal", left_digits=4, right_digits=2, positive=True)
    max_correlation_with_portfolio = factory.Faker("pydecimal", left_digits=4, right_digits=2, positive=True)
    risk_per_trade_percent = factory.Faker("pydecimal", left_digits=4, right_digits=2, positive=True)
    use_trailing_stop = factory.Faker("boolean")
    trailing_stop_config = factory.Dict({"activation_percent": 1.0, "trail_percent": 0.5})
    use_ai_risk_model = factory.Faker("boolean")


class RiskRuleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RiskRule

    profile = factory.SubFactory(RiskProfileFactory)
    name = factory.Sequence(lambda n: f"Rule {n}")
    description = factory.Faker("sentence")
    rule_type = factory.Faker("word")
    parameters = factory.Dict({"param1": "value1"})
    is_active = factory.Faker("boolean")
    priority = factory.Faker("pyint", min_value=0, max_value=10)
    action = factory.Iterator(["ALLOW", "DENY", "ADJUST"])
    agent_responsible = factory.SubFactory(AgentFactory)


class RiskEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RiskEvent

    profile = factory.SubFactory(RiskProfileFactory)
    bot = factory.SubFactory(BotFactory)
    agent = factory.SubFactory(AgentFactory)
    strategy_version = factory.SubFactory(StrategyVersionFactory)
    signal = factory.SubFactory(SignalFactory)
    order = factory.SubFactory(OrderFactory)
    position = factory.SubFactory(PositionFactory)

    event_type = factory.Iterator([
        "LIMIT_BREACHED", "STOP_LOSS_TRIGGERED", "RULE_VIOLATION", "WARNING", "LIQUIDATION", "RISK_MODEL_OVERRIDE"
    ])
    severity = factory.Iterator([1, 2, 3, 4, 5])
    message = factory.Faker("sentence")
    details = factory.Dict({"extra": "data"})
    is_resolved = factory.Faker("boolean")
    resolved_at = factory.Faker("date_time_this_month", tzinfo=None)
    resolution_notes = factory.Faker("sentence")
    correlation_id = factory.Faker("uuid4", cast_to=str)


class RiskMetricFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RiskMetric

    profile = factory.SubFactory(RiskProfileFactory)
    bot = factory.SubFactory(BotFactory)
    agent = factory.SubFactory(AgentFactory)
    timestamp = factory.Faker("date_time_this_month", tzinfo=None)

    value_at_risk = factory.Faker("pydecimal", left_digits=12, right_digits=8, positive=True)
    max_drawdown = factory.Faker("pydecimal", left_digits=8, right_digits=4, positive=True)
    sharpe_ratio = factory.Faker("pydecimal", left_digits=3, right_digits=6, allow_nan=True)
    volatility = factory.Faker("pydecimal", left_digits=3, right_digits=6, allow_nan=True)
    exposure = factory.Faker("pydecimal", left_digits=12, right_digits=8, positive=True)
    exposure_per_instrument = factory.Dict({"BTCUSDT": 5000})


class RiskAlertFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RiskAlert

    profile = factory.SubFactory(RiskProfileFactory)
    bot = factory.SubFactory(BotFactory)
    agent = factory.SubFactory(AgentFactory)

    alert_type = factory.Iterator([
        "THRESHOLD_BREACH", "RULE_VIOLATION", "HIGH_RISK_SIGNAL", "SYSTEM_ANOMALY"
    ])
    severity = factory.Iterator([1, 2, 3, 4, 5])
    title = factory.Faker("sentence")
    description = factory.Faker("paragraph")
    details = factory.Dict({"extra": "info"})
    is_acknowledged = factory.Faker("boolean")
    acknowledged_at = factory.Faker("date_time_this_month", tzinfo=None)
    acknowledged_by = factory.SubFactory(UserFactory)
    correlation_id = factory.Faker("uuid4", cast_to=str)