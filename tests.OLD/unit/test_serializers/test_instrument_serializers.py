# tests/unit/test_serializers/test_instrument_serializers.py
import pytest
from django.test import TestCase
from apps.instruments.models import Instrument, InstrumentGroup
from apps.instruments.serializers import InstrumentSerializer, InstrumentGroupSerializer
from tests.factories import InstrumentFactory, InstrumentGroupFactory


@pytest.mark.django_db
class TestInstrumentSerializer:
    def test_instrument_serializer(self):
        """Test instrument serializer."""
        instrument = InstrumentFactory()
        serializer = InstrumentSerializer(instrument)
        data = serializer.data

        assert data['symbol'] == instrument.symbol
        assert data['name'] == instrument.name
        assert data['base_asset'] == instrument.base_asset
        assert data['quote_asset'] == instrument.quote_asset
        assert data['is_active'] == instrument.is_active

    def test_instrument_group_serializer(self):
        """Test instrument group serializer."""
        group = InstrumentGroupFactory()
        serializer = InstrumentGroupSerializer(group)
        data = serializer.data

        assert data['name'] == group.name
        assert data['description'] == group.description