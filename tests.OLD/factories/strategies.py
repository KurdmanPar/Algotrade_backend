# tests/factories/strategies.py
import factory
from django.contrib.auth import get_user_model
from django.utils import timezone  # ✅ اضافه شد
from apps.strategies.models import Strategy, StrategyVersion



User = get_user_model()


class StrategyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Strategy

    owner = factory.SubFactory('tests.factories.users.UserFactory')
    name = factory.Sequence(lambda n: f"Strategy {n}")
    description = factory.Faker('text')
    category = "FULL"
    is_active = True
    is_public = False  # ✅ اضافه شد
    created_at = factory.LazyAttribute(lambda _: timezone.now())
    updated_at = factory.LazyAttribute(lambda _: timezone.now())

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