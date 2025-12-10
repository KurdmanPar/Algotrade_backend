# tests/unit/test_models/test_strategies.py
import pytest
from django.test import TestCase
from apps.strategies.models import Strategy, StrategyVersion
from tests.factories import StrategyFactory, StrategyVersionFactory


@pytest.mark.django_db
class TestStrategyModel:
    def test_strategy_creation(self):
        """Test creating a strategy."""
        strategy = StrategyFactory()
        assert strategy.name is not None
        assert strategy.owner is not None
        assert strategy.category == "FULL"
        assert strategy.is_active is True

    def test_strategy_str(self):
        """Test strategy string representation."""
        strategy = StrategyFactory()
        # اصلاح شده: با فرمت جدید __str__ مطابقت دارد
        assert str(strategy) == f"{strategy.name} ({strategy.owner.email})"

    def test_strategy_version_creation(self):
        """Test creating a strategy version."""
        version = StrategyVersionFactory()
        assert version.strategy is not None
        assert version.version is not None
        assert version.parameters_schema is not None
        assert version.indicator_configs is not None
        assert version.is_approved_for_live is False

    def test_strategy_version_str(self):
        """Test strategy version string representation."""
        version = StrategyVersionFactory()
        assert str(version) == f"{version.strategy.name} v{version.version}"