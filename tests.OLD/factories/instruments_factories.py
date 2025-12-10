# tests/factories/instruments_factories.py
import factory
from apps.instruments.models import (
    InstrumentGroup, InstrumentCategory, Instrument, InstrumentExchangeMap,
    IndicatorGroup, Indicator, IndicatorParameter, IndicatorTemplate,
    PriceActionPattern, SmartMoneyConcept, AIMetric
)
from tests.factories.accounts_factories import UserFactory
from tests.factories.exchanges_factories import ExchangeFactory


class InstrumentGroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InstrumentGroup

    name = factory.Sequence(lambda n: f"Instrument Group {n}")
    description = factory.Faker("sentence")


class InstrumentCategoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InstrumentCategory

    name = factory.Sequence(lambda n: f"Instrument Category {n}")
    description = factory.Faker("sentence")


class InstrumentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Instrument

    symbol = factory.Sequence(lambda n: f"SYM{n}")
    name = factory.Faker("company")
    group = factory.SubFactory(InstrumentGroupFactory)
    category = factory.SubFactory(InstrumentCategoryFactory)
    base_asset = factory.Faker("currency_code")
    quote_asset = factory.Faker("currency_code")
    tick_size = factory.Faker("pydecimal", left_digits=3, right_digits=8, positive=True)
    lot_size = factory.Faker("pydecimal", left_digits=2, right_digits=8, positive=True)
    is_active = factory.Faker("boolean")
    metadata = factory.Dict({"key": "value"})


class InstrumentExchangeMapFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = InstrumentExchangeMap

    instrument = factory.SubFactory(InstrumentFactory)
    exchange = factory.SubFactory(ExchangeFactory)
    exchange_symbol = factory.LazyAttribute(lambda obj: f"{obj.instrument.symbol.lower()}{obj.exchange.code.lower()}")
    is_active = factory.Faker("boolean")


class IndicatorGroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = IndicatorGroup

    name = factory.Sequence(lambda n: f"Indicator Group {n}")
    description = factory.Faker("sentence")


class IndicatorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Indicator

    name = factory.Sequence(lambda n: f"Indicator {n}")
    code = factory.LazyAttribute(lambda obj: obj.name.upper().replace(" ", "_"))
    group = factory.SubFactory(IndicatorGroupFactory)
    description = factory.Faker("sentence")
    is_active = factory.Faker("boolean")
    is_builtin = factory.Faker("boolean")
    version = factory.Faker("numerify", text="1.0.#")


class IndicatorParameterFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = IndicatorParameter

    indicator = factory.SubFactory(IndicatorFactory)
    name = factory.Faker("word")
    display_name = factory.Faker("sentence")
    data_type = factory.Iterator(["int", "float", "bool", "str", "choice"])
    default_value = factory.Faker("word")
    min_value = factory.Faker("word")
    max_value = factory.Faker("word")
    choices = factory.Faker("words", nb=3)


class IndicatorTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = IndicatorTemplate

    name = factory.Sequence(lambda n: f"Template {n}")
    indicator = factory.SubFactory(IndicatorFactory)
    description = factory.Faker("sentence")
    parameters = factory.Dict({"period": 14, "matype": 0})
    is_active = factory.Faker("boolean")


class PriceActionPatternFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = PriceActionPattern

    name = factory.Sequence(lambda n: f"Pattern {n}")
    code = factory.LazyAttribute(lambda obj: obj.name.upper().replace(" ", "_"))
    description = factory.Faker("sentence")
    is_active = factory.Faker("boolean")


class SmartMoneyConceptFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = SmartMoneyConcept

    name = factory.Sequence(lambda n: f"SMC {n}")
    code = factory.LazyAttribute(lambda obj: obj.name.upper().replace(" ", "_"))
    description = factory.Faker("sentence")
    is_active = factory.Faker("boolean")


class AIMetricFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AIMetric

    name = factory.Sequence(lambda n: f"AI Metric {n}")
    code = factory.LazyAttribute(lambda obj: obj.name.upper().replace(" ", "_"))
    description = factory.Faker("sentence")
    data_type = factory.Iterator(["FLOAT", "INT", "BOOL", "STR"])
    is_active = factory.Faker("boolean")