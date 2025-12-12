# apps/core/registry.py

import logging
from typing import Dict, Type, Any, Optional
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.module_loading import import_string

logger = logging.getLogger(__name__)

class SingletonRegistry(type):
    """
    Metaclass for creating a singleton registry instance.
    Ensures only one instance of the registry exists throughout the application lifecycle.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonRegistry, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class ConnectorRegistry(metaclass=SingletonRegistry):
    """
    Central registry for managing different data connectors (e.g., Binance, Coinbase, Custom Exchange API).
    Allows for dynamic loading and instantiation of connector classes based on their name/type.
    This facilitates switching data sources without changing core code.
    """
    def __init__(self):
        self._connectors: Dict[str, Type] = {}
        self._initialized = False

    def register_connector(self, name: str, connector_class: Type):
        """
        Registers a connector class with its unique name/type identifier.
        Args:
            name: A unique string identifier for the connector (e.g., 'binance', 'coinbase', 'nobitex', 'lbank').
            connector_class: The class of the connector to register.
        """
        if name in self._connectors:
            logger.warning(f"Connector '{name}' is already registered. Overwriting.")
        self._connectors[name] = connector_class
        logger.info(f"Connector class {connector_class.__name__} registered with name '{name}'.")

    def unregister_connector(self, name: str):
        """
        Removes a connector class from the registry.
        """
        if name in self._connectors:
            del self._connectors[name]
            logger.info(f"Connector type '{name}' unregistered.")
        else:
            logger.warning(f"Attempted to unregister non-existent connector type '{name}'.")

    def get_connector_class(self, name: str) -> Optional[Type]:
        """
        Retrieves the connector class associated with a specific name/type.
        Returns None if the name/type is not found.
        """
        return self._connectors.get(name)

    def instantiate_connector(self, name: str, **kwargs) -> Optional[Any]:
        """
        Instantiates a connector based on its registered name/type and provided configuration.
        Args:
            name: The name/type of connector to instantiate.
            **kwargs: Additional arguments to pass to the connector's constructor (e.g., api_key, api_secret).
        Returns:
            An instance of the connector class or None if the type is not found or instantiation fails.
        """
        connector_class = self.get_connector_class(name)
        if not connector_class:
            logger.error(f"Connector type '{name}' not found in registry.")
            return None

        try:
            # ایجاد نمونه از کلاس کانکتور با آرگومان‌های ارائه شده
            connector_instance = connector_class(**kwargs)
            logger.info(f"Connector instance of type '{name}' created successfully.")
            return connector_instance
        except Exception as e:
            logger.error(f"Failed to instantiate connector of type '{name}': {str(e)}")
            return None

    def list_registered_connectors(self) -> Dict[str, str]:
        """
        Returns a dictionary of registered connector names and their class names.
        Useful for introspection or UI purposes.
        """
        return {k: v.__name__ for k, v in self._connectors.items()}

    def initialize_from_settings(self):
        """
        Initializes the registry by loading connector classes defined in Django settings.
        Example setting: CORE_CONNECTOR_REGISTRY = {'binance': 'apps.connectors.binance.BinanceConnector', 'nobitex': 'apps.connectors.nobitex.NobitexConnector', ...}
        """
        if self._initialized:
            logger.warning("Connector registry is already initialized.")
            return

        connector_classes = getattr(settings, 'CORE_CONNECTOR_REGISTRY', {})
        for conn_name, conn_path in connector_classes.items():
            try:
                # استفاده از import_string برای بارگذاری پویای کلاس
                connector_class = import_string(conn_path)
                self.register_connector(conn_name, connector_class)
            except (ImportError, AttributeError) as e:
                logger.error(f"Failed to load connector class '{conn_path}' for name '{conn_name}': {e}")
                # بر اساس نیاز، می‌توانید یک ImproperlyConfigured صادر کنید تا راه‌اندازی پروژه متوقف شود
                # raise ImproperlyConfigured(f"Connector class '{conn_path}' could not be loaded: {e}")

        self._initialized = True
        logger.info("Connector registry initialized from settings.")

# --- مثال: ثبت کانکتورهای Nobitex و LBank ---
# این مثال فرض می‌کند که کلاس‌های کانکتور مربوطه در مسیرهای زیر تعریف شده‌اند:
# apps/connectors/nobitex.py -> class NobitexConnector
# apps/connectors/lbank.py -> class LbankConnector

# در فایل settings.py پروژه:
# CORE_CONNECTOR_REGISTRY = {
#     'binance': 'apps.connectors.binance.BinanceConnector',
#     'coinbase': 'apps.connectors.coinbase.CoinbaseConnector',
#     'nobitex': 'apps.connectors.nobitex.NobitexConnector',
#     'lbank': 'apps.connectors.lbank.LbankConnector',
# }

# یا می‌توانید به صورت دستی در ready() اپلیکیشن خود (مثلاً apps/core/apps.py یا apps/connectors/apps.py) نیز ثبت کنید:
# from apps.core.registry import ConnectorRegistry
# from apps.connectors.nobitex import NobitexConnector
# from apps.connectors.lbank import LbankConnector
#
# registry = ConnectorRegistry()
# registry.register_connector('nobitex', NobitexConnector)
# registry.register_connector('lbank', LbankConnector)

# --- مثال: استفاده از رجیستری در یک سرویس ---
# class DataFetchingService:
#     def fetch_data(self, exchange_name, symbol, timeframe):
#         registry = ConnectorRegistry()
#         connector = registry.instantiate_connector(exchange_name)
#         if connector:
#             return connector.get_ohlcv(symbol, timeframe)
#         else:
#             raise ValueError(f"No connector available for exchange: {exchange_name}")


class StrategyRegistry(metaclass=SingletonRegistry):
    """
    Registry for trading strategies.
    Allows dynamic loading and selection of strategy classes.
    """
    def __init__(self):
        self._strategies: Dict[str, Type] = {}
        self._initialized = False

    def register_strategy(self, name: str, strategy_class: Type):
        if name in self._strategies:
            logger.warning(f"Strategy '{name}' is already registered. Overwriting.")
        self._strategies[name] = strategy_class
        logger.info(f"Strategy class {strategy_class.__name__} registered with name '{name}'.")

    def get_strategy_class(self, name: str) -> Optional[Type]:
        return self._strategies.get(name)

    def instantiate_strategy(self, name: str, **kwargs) -> Optional[Any]:
        strategy_class = self.get_strategy_class(name)
        if not strategy_class:
            logger.error(f"Strategy '{name}' not found in registry.")
            return None
        try:
            return strategy_class(**kwargs)
        except Exception as e:
            logger.error(f"Failed to instantiate strategy '{name}': {str(e)}")
            return None

    def initialize_from_settings(self):
        """
        Initializes the registry by loading strategy classes defined in Django settings.
        Example setting: CORE_STRATEGY_REGISTRY = {'sma_crossover': 'apps.strategies.sma_crossover.SMACrossoverStrategy', ...}
        """
        if self._initialized:
            logger.warning("Strategy registry is already initialized.")
            return

        strategy_classes = getattr(settings, 'CORE_STRATEGY_REGISTRY', {})
        for strat_name, strat_path in strategy_classes.items():
            try:
                strategy_class = import_string(strat_path)
                self.register_strategy(strat_name, strategy_class)
            except (ImportError, AttributeError) as e:
                logger.error(f"Failed to load strategy class '{strat_path}' for name '{strat_name}': {e}")
                # raise ImproperlyConfigured(f"Strategy class '{strat_path}' could not be loaded: {e}")

        self._initialized = True
        logger.info("Strategy registry initialized from settings.")


# --- مثال: رجیستری برای عامل‌ها (Agents) ---
class AgentRegistry(metaclass=SingletonRegistry):
    """
    Registry for different types of MAS agents (e.g., Data Collector, Risk Manager, Order Executor).
    """
    def __init__(self):
        self._agents: Dict[str, Type] = {}
        self._initialized = False

    def register_agent(self, agent_type: str, agent_class: Type):
        if agent_type in self._agents:
            logger.warning(f"Agent type '{agent_type}' is already registered. Overwriting.")
        self._agents[agent_type] = agent_class
        logger.info(f"Agent class {agent_class.__name__} registered for type '{agent_type}'.")

    def get_agent_class(self, agent_type: str) -> Optional[Type]:
        return self._agents.get(agent_type)

    def instantiate_agent(self, agent_type: str, **kwargs) -> Optional[Any]:
        agent_class = self.get_agent_class(agent_type)
        if not agent_class:
            logger.error(f"Agent type '{agent_type}' not found in registry.")
            return None
        try:
            return agent_class(**kwargs)
        except Exception as e:
            logger.error(f"Failed to instantiate agent of type '{agent_type}': {str(e)}")
            return None

    def initialize_from_settings(self):
        """
        Initializes the registry by loading agent classes defined in Django settings.
        Example setting: CORE_AGENT_REGISTRY = {'data_collector': 'apps.agents.data_collector.DataCollectorAgent', ...}
        """
        if self._initialized:
            logger.warning("Agent registry is already initialized.")
            return

        agent_classes = getattr(settings, 'CORE_AGENT_REGISTRY', {})
        for agent_type, agent_path in agent_classes.items():
            try:
                agent_class = import_string(agent_path)
                self.register_agent(agent_type, agent_class)
            except (ImportError, AttributeError) as e:
                logger.error(f"Failed to load agent class '{agent_path}' for type '{agent_type}': {e}")
                # raise ImproperlyConfigured(f"Agent class '{agent_path}' could not be loaded: {e}")

        self._initialized = True
        logger.info("Agent registry initialized from settings.")

# --- مثال: استفاده ---
# registry = ConnectorRegistry()
# registry.initialize_from_settings() # در ready() اپلیکیشن یا هنگام شروع سیستم
# connector = registry.instantiate_connector('nobitex', api_key='key', api_secret='secret')
# data = connector.fetch_ohlcv('BTCIRT', '1h')

logger.info("Registry components loaded.")
