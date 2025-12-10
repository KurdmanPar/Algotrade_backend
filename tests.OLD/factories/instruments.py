# tests/factories/instruments.py
import factory
from apps.instruments.models import Instrument, InstrumentGroup, Indicator, IndicatorGroup


class InstrumentGroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InstrumentGroup

    name = factory.Sequence(lambda n: f"Group {n}")
    description = factory.Faker('text')


class InstrumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Instrument

    symbol = factory.Sequence(lambda n: f"SYMBOL{n}")
    name = factory.Faker('company')  # این فیلد در مدل وجود دارد
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