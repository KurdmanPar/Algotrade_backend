# tests/factories/strategies_factories.py
import factory
from apps.strategies.models import Strategy, StrategyVersion, StrategyAssignment
from tests.factories.accounts_factories import UserFactory
# از bots_factories اینجا import نکنید، چون چرخه ایجاد می‌شود
# from tests.factories.bots_factories import BotFactory

class StrategyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Strategy

    owner = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: f"Strategy {n}")
    description = factory.Faker("sentence")
    category = factory.Iterator([
        "ENTRY", "EXIT", "FULL", "RISK", "ML", "AI", "PRICE_ACTION", "SMART_MONEY"
    ])
    is_active = factory.Faker("boolean")
    is_public = factory.Faker("boolean")
    risk_level = factory.Iterator(["low", "medium", "high"])
    source_code_encrypted = factory.Faker("password")
    code_language = "Python"

class StrategyVersionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StrategyVersion

    strategy = factory.SubFactory(StrategyFactory)
    version = factory.Sequence(lambda n: f"1.0.{n}")
    parameters_schema = factory.Dict({"param1": "int", "param2": "float"})
    indicator_configs = factory.List([factory.Dict({"name": "RSI", "params": {"period": 14}})])
    price_action_configs = factory.List([])
    smart_money_configs = factory.List([])
    ai_metrics_configs = factory.List([])
    source_code_ref = factory.Faker("uri_path")
    model_artifact_ref = factory.Faker("uri_path")
    is_approved_for_live = factory.Faker("boolean")

class StrategyAssignmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StrategyAssignment

    # نباید BotFactory را اینجا import کنیم
    # پس در تست، این را به صورت دستی ایجاد خواهیم کرد
    # bot = factory.SubFactory(BotFactory)
    # strategy_version = factory.SubFactory(StrategyVersionFactory)

    # weight، priority و سایر فیلدها را می‌توانیم اینجا تعریف کنیم
    weight = factory.Faker("pyfloat", min_value=0.1, max_value=1.0)
    priority = factory.Faker("pyint", min_value=0, max_value=10)
    parameters_override = factory.Dict({"param1": 100})
    is_active = factory.Faker("boolean")