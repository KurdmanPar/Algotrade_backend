# tests/unit/test_serializers/test_instrument_serializers.py
import pytest
from apps.instruments.serializers import InstrumentSerializer
from tests.factories.instruments_factories import InstrumentFactory

@pytest.mark.django_db
def test_instrument_serializer_valid():
    instrument = InstrumentFactory()
    serializer = InstrumentSerializer(instrument)
    data = serializer.data
    assert data['symbol'] == instrument.symbol
    assert data['name'] == instrument.name
    assert 'owner' in data