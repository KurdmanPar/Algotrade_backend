# tests/test_core/test_registry.py

import pytest
from unittest.mock import patch, MagicMock
from django.conf import settings
from apps.core.registry import (
    ConnectorRegistry,
    StrategyRegistry,
    AgentRegistry,
    # سایر رجیستری‌های شما
)
from apps.core.models import SystemSetting # ممکن است برای تست رجیستری از طریق تنظیمات نیاز باشد
from apps.accounts.models import CustomUser # فرض بر این است که مدل کاربر وجود دارد
from apps.instruments.models import Instrument # فرض بر این است که مدل نماد وجود دارد
from apps.exchanges.models import Exchange # فرض بر این است که مدل صرافی وجود دارد
# ایمپورت کلاس‌هایی که قرار است ثبت شوند
# from apps.connectors.binance import BinanceConnector
# from apps.connectors.coinbase import CoinbaseConnector
# from apps.strategies.sma import SMACrossoverStrategy
# from apps.agents.data_collector import DataCollectorAgent

pytestmark = pytest.mark.django_db

class TestConnectorRegistry:
    """
    Tests for the ConnectorRegistry class.
    """
    def test_singleton_behavior(self):
        """
        Test that ConnectorRegistry follows the Singleton pattern.
        """
        reg1 = ConnectorRegistry()
        reg2 = ConnectorRegistry()
        assert reg1 is reg2

    def test_register_and_get_connector_class(self):
        """
        Test registering a connector class and retrieving it.
        """
        # ایجاد یک کلاس کانکتور ساختگی برای تست
        class MockConnector:
            pass

        registry = ConnectorRegistry()
        registry.register_connector('mock_conn', MockConnector)

        retrieved_class = registry.get_connector_class('mock_conn')
        assert retrieved_class is MockConnector

    def test_instantiate_connector_success(self, mocker):
        """
        Test instantiating a registered connector class.
        """
        class MockConnector:
            def __init__(self, **kwargs):
                self.config = kwargs

        registry = ConnectorRegistry()
        registry.register_connector('mock_conn', MockConnector)

        config_data = {'api_key': 'key', 'secret': 'secret'}
        # Mock کردن سازنده کلاس
        mock_constructor = mocker.patch.object(MockConnector, '__init__', return_value=None)

        instance = registry.instantiate_connector('mock_conn', **config_data)

        assert instance is not None
        mock_constructor.assert_called_once_with(**config_data)

    def test_instantiate_connector_not_found(self):
        """
        Test instantiating a non-registered connector class.
        """
        registry = ConnectorRegistry()
        instance = registry.instantiate_connector('non_existent_conn', api_key='test')
        assert instance is None

    def test_initialize_from_settings(self, mocker):
        """
        Test initializing the registry from Django settings.
        """
        # Mock کردن import_string
        mock_import = mocker.patch('apps.core.registry.import_string')
        mock_connector_class = mocker.Mock()
        mock_import.return_value = mock_connector_class

        # ایجاد یک تنظیم موقت در settings
        with patch.dict(settings._wrapped.__dict__, {'CORE_CONNECTOR_REGISTRY': {'binance': 'apps.connectors.binance.BinanceConnector'}}):
            registry = ConnectorRegistry()
            registry.initialize_from_settings()

        # چک کردن اینکه import_string یک بار با مسیر صحیح فراخوانی شده است
        mock_import.assert_called_once_with('apps.connectors.binance.BinanceConnector')
        # چک کردن اینکه کلاس ثبت شده است
        assert registry.get_connector_class('binance') == mock_connector_class


class TestStrategyRegistry:
    """
    Tests for the StrategyRegistry class.
    """
    def test_singleton_behavior(self):
        """
        Test that StrategyRegistry follows the Singleton pattern.
        """
        reg1 = StrategyRegistry()
        reg2 = StrategyRegistry()
        assert reg1 is reg2

    def test_register_and_get_strategy_class(self):
        """
        Test registering a strategy class and retrieving it.
        """
        class MockStrategy:
            pass

        registry = StrategyRegistry()
        registry.register_strategy('mock_strat', MockStrategy)

        retrieved_class = registry.get_strategy_class('mock_strat')
        assert retrieved_class is MockStrategy

    def test_instantiate_strategy_success(self, mocker):
        """
        Test instantiating a registered strategy class.
        """
        class MockStrategy:
            def __init__(self, **kwargs):
                self.params = kwargs

        registry = StrategyRegistry()
        registry.register_strategy('mock_strat', MockStrategy)

        param_data = {'param1': 'value1', 'param2': 'value2'}
        mock_constructor = mocker.patch.object(MockStrategy, '__init__', return_value=None)

        instance = registry.instantiate_strategy('mock_strat', **param_data)

        assert instance is not None
        mock_constructor.assert_called_once_with(**param_data)

    def test_instantiate_strategy_not_found(self):
        """
        Test instantiating a non-registered strategy class.
        """
        registry = StrategyRegistry()
        instance = registry.instantiate_strategy('non_existent_strat', param1='val')
        assert instance is None

    def test_initialize_from_settings(self, mocker):
        """
        Test initializing the registry from Django settings.
        """
        mock_import = mocker.patch('apps.core.registry.import_string')
        mock_strategy_class = mocker.Mock()
        mock_import.return_value = mock_strategy_class

        with patch.dict(settings._wrapped.__dict__, {'CORE_STRATEGY_REGISTRY': {'sma_cross': 'apps.strategies.sma.SMACrossoverStrategy'}}):
            registry = StrategyRegistry()
            registry.initialize_from_settings()

        mock_import.assert_called_once_with('apps.strategies.sma.SMACrossoverStrategy')
        assert registry.get_strategy_class('sma_cross') == mock_strategy_class


class TestAgentRegistry:
    """
    Tests for the AgentRegistry class.
    """
    def test_singleton_behavior(self):
        """
        Test that AgentRegistry follows the Singleton pattern.
        """
        reg1 = AgentRegistry()
        reg2 = AgentRegistry()
        assert reg1 is reg2

    def test_register_and_get_agent_class(self):
        """
        Test registering an agent class and retrieving it.
        """
        class MockAgent:
            pass

        registry = AgentRegistry()
        registry.register_agent('mock_agent', MockAgent)

        retrieved_class = registry.get_agent_class('mock_agent')
        assert retrieved_class is MockAgent

    def test_instantiate_agent_success(self, mocker, CustomUserFactory):
        """
        Test instantiating a registered agent class.
        """
        user = CustomUserFactory()
        class MockAgent:
            def __init__(self, agent_config, **kwargs):
                self.agent_config = agent_config
                self.owner = kwargs.get('owner')

        registry = AgentRegistry()
        registry.register_agent('mock_agent', MockAgent)

        config_data = {'type': 'data_collector', 'settings': {}}
        mock_constructor = mocker.patch.object(MockAgent, '__init__', return_value=None)

        instance = registry.instantiate_agent('mock_agent', config_data, owner=user)

        assert instance is not None
        mock_constructor.assert_called_once_with(agent_config=config_data, owner=user)

    def test_instantiate_agent_not_found(self, CustomUserFactory):
        """
        Test instantiating a non-registered agent class.
        """
        user = CustomUserFactory()
        registry = AgentRegistry()
        instance = registry.instantiate_agent('non_existent_agent', {}, owner=user)
        assert instance is None

    def test_initialize_from_settings(self, mocker, CustomUserFactory):
        """
        Test initializing the registry from Django settings.
        """
        user = CustomUserFactory()
        mock_import = mocker.patch('apps.core.registry.import_string')
        mock_agent_class = mocker.Mock()
        mock_import.return_value = mock_agent_class

        with patch.dict(settings._wrapped.__dict__, {'CORE_AGENT_REGISTRY': {'data_collector': 'apps.agents.data_collector.DataCollectorAgent'}}):
            registry = AgentRegistry()
            registry.initialize_from_settings()

        mock_import.assert_called_once_with('apps.agents.data_collector.DataCollectorAgent')
        assert registry.get_agent_class('data_collector') == mock_agent_class

    def test_list_registered_agents(self):
        """
        Test the list_registered_agents method.
        """
        class AgentA: pass
        class AgentB: pass

        registry = AgentRegistry()
        registry.register_agent('type_a', AgentA)
        registry.register_agent('type_b', AgentB)

        registered_list = registry.list_registered_agents()
        assert 'type_a' in registered_list
        assert 'type_b' in registered_list
        assert registered_list['type_a'] == 'AgentA'
        assert registered_list['type_b'] == 'AgentB'

# --- تست سایر رجیستری‌های ممکن ---
# می‌توانید برای سایر رجیستری‌هایی که ایجاد می‌کنید نیز تست بنویسید
# مثلاً اگر یک RiskRuleRegistry داشتید:
# class TestRiskRuleRegistry:
#     ...

logger.info("Core registry tests loaded successfully.")
