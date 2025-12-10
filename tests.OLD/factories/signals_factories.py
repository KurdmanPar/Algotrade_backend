# tests/factories/signals_factories.py
import factory
from apps.signals.models import Signal, SignalLog, SignalAlert
from tests.factories.accounts_factories import UserFactory
from tests.factories.bots_factories import BotFactory
from tests.factories.strategies_factories import StrategyVersionFactory
from tests.factories.instruments_factories import InstrumentFactory

class SignalFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Signal

    user = factory.SubFactory(UserFactory)
    bot = factory.SubFactory(BotFactory)
    strategy_version = factory.SubFactory(StrategyVersionFactory)
    instrument = factory.SubFactory(InstrumentFactory)

    direction = factory.Iterator(["BUY", "SELL", "CLOSE_LONG", "CLOSE_SHORT"])
    signal_type = factory.Iterator([
        "ENTRY", "EXIT", "TAKE_PROFIT", "STOP_LOSS", "SCALE_IN", "SCALE_OUT"
    ])
    price = factory.Faker("pydecimal", left_digits=10, right_digits=8, positive=True)
    quantity = factory.Faker("pydecimal", left_digits=6, right_digits=8, positive=True)
    confidence_score = factory.Faker("pyfloat", min_value=0.0, max_value=1.0)
    payload = factory.PostGenerationMethodCall('json', '{}')

    status = factory.Iterator(["PENDING", "APPROVED", "REJECTED", "EXECUTED", "EXPIRED"])

    correlation_id = factory.Faker("uuid4", cast_to=str)


class SignalLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SignalLog

    signal = factory.SubFactory(SignalFactory)
    old_status = factory.Iterator(["PENDING", "APPROVED", "REJECTED", "EXECUTED", "EXPIRED"])
    new_status = factory.Iterator(["APPROVED", "REJECTED", "EXECUTED", "EXPIRED", "PENDING"])
    message = factory.Faker("sentence")
    details = factory.PostGenerationMethodCall('json', '{}')


class SignalAlertFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SignalAlert

    signal = factory.SubFactory(SignalFactory)
    alert_type = factory.Iterator(["HIGH_CONFIDENCE", "RISK_ALERT", "EXECUTION_FAILED"])
    severity = factory.Iterator([1, 2, 3, 4, 5])
    title = factory.Faker("sentence", nb_words=6)
    description = factory.Faker("paragraph", nb_sentences=3)
    details = factory.PostGenerationMethodCall('json', '{}')
    is_acknowledged = factory.Faker("boolean")
    acknowledged_at = factory.Faker("date_time_this_month", tzinfo=None)