# tests/unit/test_models/test_instruments.py
import pytest
from tests.factories.instruments_factories import InstrumentFactory, IndicatorFactory

@pytest.mark.django_db
def test_instrument_creation():
    instrument = InstrumentFactory()
    assert instrument.symbol is not None
    assert instrument.owner is not None
    assert instrument.is_active is True

@pytest.mark.django_db
def test_indicator_creation():
    indicator = IndicatorFactory()
    assert indicator.code is not None
    assert indicator.owner is not None
    assert indicator.is_active is True