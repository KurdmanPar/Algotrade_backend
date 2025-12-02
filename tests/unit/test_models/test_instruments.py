# tests/unit/test_models/test_instruments.py
import pytest
from django.test import TestCase
from apps.instruments.models import Instrument, InstrumentGroup, Indicator, IndicatorGroup
from tests.factories import InstrumentFactory, InstrumentGroupFactory, IndicatorFactory, IndicatorGroupFactory


@pytest.mark.django_db
class TestInstrumentModel:
    def test_instrument_creation(self):
        """Test creating an instrument."""
        instrument = InstrumentFactory()
        assert instrument.symbol is not None
        assert instrument.name is not None  # این فیلد در مدل وجود دارد
        assert instrument.group is not None
        assert instrument.base_asset is not None
        assert instrument.quote_asset is not None

    def test_instrument_str(self):
        """Test instrument string representation."""
        instrument = InstrumentFactory()
        # اصلاح شده: با فرمت جدید __str__ مطابقت دارد
        assert str(instrument) == f"{instrument.symbol} ({instrument.name})"

    def test_instrument_group_creation(self):
        """Test creating an instrument group."""
        group = InstrumentGroupFactory()
        assert group.name is not None
        assert group.description is not None

    def test_indicator_creation(self):
        """Test creating an indicator."""
        indicator = IndicatorFactory()
        assert indicator.name is not None
        assert indicator.code is not None
        assert indicator.group is not None

    def test_indicator_str(self):
        """Test indicator string representation."""
        indicator = IndicatorFactory()
        # اصلاح شده: با فرمت جدید __str__ مطابقت دارد
        assert str(indicator) == f"{indicator.name} ({indicator.code})"