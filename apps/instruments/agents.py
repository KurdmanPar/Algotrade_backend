# apps/instruments/agents.py

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import aiohttp
import websockets
from decimal import Decimal

from django.conf import settings
from django.utils import timezone
from apps.core.agents import BaseAgent # فرض بر این است که یک کلاس پایه برای عامل‌ها وجود دارد
from apps.core.exceptions import AgentError, ConfigurationError
from apps.core.logging import get_logger # فرض بر این است که یک سیستم لاگ مرکزی دارید
from apps.core.messaging import MessageBus # فرض بر این است که یک سیستم پیام‌رسانی وجود دارد
from .models import Instrument, InstrumentExchangeMap
from .services import InstrumentService
from apps.connectors.service import ConnectorService # فرض بر این است که این سرویس وجود دارد
from apps.market_data.services import MarketDataService # فرض بر این است که این سرویت وجود دارد

logger = get_logger(__name__)

class InstrumentDataCollectorAgent(BaseAgent):
    """
    Agent responsible for collecting market data for specific instruments.
    It manages subscriptions to exchanges via WebSocket or polling REST APIs,
    normalizes the data, and publishes it to the internal message bus for other agents (e.g., StrategyAgent).
    This agent represents the "Data Acquisition Agent" mentioned in the MAS context.
    """
    def __init__(self, agent_config: Dict[str, Any]):
        super().__init__(agent_config)
        self.name = agent_config.get("name", "InstrumentDataCollector")
        self.instruments_to_monitor = agent_config.get("instruments", []) # لیست ID یا Symbol
        self.subscription_type = agent_config.get("subscription_type", "ticker") # e.g., ticker, kline_1m, orderbook
        self.polling_interval = agent_config.get("polling_interval", 1.0) # ثانیه (برای REST)
        self.ws_reconnect_delay = agent_config.get("ws_reconnect_delay", 5) # ثانیه
        self._active_ws_connections = {} # {instrument_symbol: websocket_connection}
        self._connector_service = ConnectorService()
        self._market_data_service = MarketDataService()
        self._instrument_cache = {} # {symbol: Instrument object}

    async def initialize(self):
        """
        Initializes the agent, e.g., loads instrument list, validates configs.
        """
        logger.info(f"Initializing {self.name} agent.")
        try:
            # 1. تأیید ابزارهای مورد نظر
            self._instrument_objects = await self._load_instruments(self.instruments_to_monitor)
            if not self._instrument_objects:
                 raise ConfigurationError(f"{self.name} agent: No valid instruments found for monitoring.")

            # 2. تأیید نوع اشتراک
            valid_types = ["ticker", "kline_1m", "kline_5m", "kline_1h", "orderbook", "trade"] # و یا از مدل/کانفیگ بخوانید
            if self.subscription_type not in valid_types:
                 raise ConfigurationError(f"{self.name} agent: Invalid subscription type '{self.subscription_type}'. Must be one of {valid_types}.")

            logger.info(f"Initialized {self.name} to monitor {len(self._instrument_objects)} instruments: {[inst.symbol for inst in self._instrument_objects]}")
        except Exception as e:
            logger.error(f"Failed to initialize {self.name} agent: {str(e)}")
            raise # یا مدیریت خطا مناسب


    async def _load_instruments(self, symbols_or_ids: List[str]) -> List[Instrument]:
        """
        Loads Instrument objects from the database based on symbols or IDs.
        """
        instruments = []
        for identifier in symbols_or_ids:
            try:
                # سعی در یافتن بر اساس ID (اگر عدد باشد)
                if identifier.isdigit():
                    inst = await Instrument.objects.aget(id=int(identifier))
                else:
                    # در غیر این صورت، بر اساس Symbol
                    inst = await Instrument.objects.aget(symbol__iexact=identifier)
                instruments.append(inst)
                self._instrument_cache[inst.symbol] = inst
            except Instrument.DoesNotExist:
                logger.warning(f"Instrument with identifier '{identifier}' not found in database. Skipping.")
                continue
        return instruments

    async def run(self):
        """
        Main execution loop for the agent.
        Depending on the configuration, it might start WebSocket listeners or polling loops.
        """
        logger.info(f"Starting {self.name} agent's main loop.")
        try:
            if self.subscription_type.startswith("kline"): # اشتراک WebSocket برای کندل
                await self._run_websocket_subscription()
            elif self.subscription_type == "ticker":
                # مثال: اشتراک WebSocket تیکر
                await self._run_websocket_subscription()
            elif self.subscription_type == "orderbook":
                # مثال: اشتراک WebSocket کتاب سفارش
                await self._run_websocket_subscription()
            else: # مثلاً "ticker" با polling
                await self._run_polling_loop()

        except asyncio.CancelledError:
            logger.info(f"{self.name} agent task was cancelled.")
        except Exception as e:
            logger.error(f"Error in {self.name} agent's run loop: {str(e)}")
            # ممکن است بخواهید دوباره شروع کنید یا خطایی را گزارش دهید
            raise

    async def _run_websocket_subscription(self):
        """
        Establishes and maintains WebSocket connections to exchanges for subscribed instruments.
        """
        logger.info(f"Starting WebSocket subscription for {self.name} on type {self.subscription_type}.")
        # 1. یافتن تمام InstrumentExchangeMapهای مرتبط با نمادهای مورد نظر و نوع اشتراک
        instrument_maps = await InstrumentExchangeMap.objects.select_related('instrument', 'exchange').filter(
            instrument__in=self._instrument_objects,
            is_active=True
        ).aiterator()

        # 2. گروه‌بندی اتصالات بر اساس صرافی
        exchange_subscriptions = {}
        async for map_obj in instrument_maps:
            exchange_name = map_obj.exchange.name
            if exchange_name not in exchange_subscriptions:
                exchange_subscriptions[exchange_name] = {'maps': [], 'ws_url': map_obj.exchange.ws_url}

            exchange_subscriptions[exchange_name]['maps'].append(map_obj)

        # 3. ایجاد یک تسک برای هر صرافی
        tasks = []
        for exchange_name, details in exchange_subscriptions.items():
            task = asyncio.create_task(self._listen_to_exchange_ws(exchange_name, details['ws_url'], details['maps']))
            tasks.append(task)

        # 4. انتظار برای تمام تسک‌ها
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True) # return_exceptions=True تا خطاها مدیریت شوند

    async def _listen_to_exchange_ws(self, exchange_name: str, ws_url: str, instrument_maps: List[InstrumentExchangeMap]):
        """
        Listens to a single WebSocket connection for an exchange.
        """
        connector = self._connector_service.get_connector(exchange_name)
        if not connector:
             logger.error(f"Connector for exchange {exchange_name} not found.")
             return

        while True: # حلقه دائمی برای اتصال مجدد
            try:
                logger.info(f"[{self.name}] Connecting to WebSocket for {exchange_name} at {ws_url}...")
                async with websockets.connect(ws_url) as ws:
                    logger.info(f"[{self.name}] Connected to {exchange_name} WebSocket.")

                    # 1. ارسال درخواست اشتراک برای تمام نمادهای مرتبط
                    for map_obj in instrument_maps:
                        # مثلاً: {'method': 'SUBSCRIBE', 'params': [f'{map_obj.exchange_symbol}@ticker'], 'id': 1}
                        sub_msg = connector.prepare_subscribe_message(map_obj.exchange_symbol, self.subscription_type)
                        await ws.send(sub_msg)
                        logger.debug(f"[{self.name}] Sent subscription for {map_obj.exchange_symbol} on {exchange_name}.")

                    # 2. حلقه گوش دادن
                    async for message in ws:
                        try:
                            raw_data = connector.parse_websocket_message(message)
                            if not raw_data:
                                continue # پیام نامعتبر

                            # 3. نرمالایز کردن داده
                            normalized_data = connector.normalize_data(raw_data, self.subscription_type)

                            # 4. یافتن نماد محلی
                            local_symbol = normalized_data.get('symbol') # این کلید بستگی به خروجی normalize دارد
                            local_instrument = self._instrument_cache.get(local_symbol)
                            if not local_instrument:
                                logger.warning(f"[{self.name}] Local instrument for symbol {local_symbol} not found in cache. Skipping data.")
                                continue

                            # 5. ذخیره در سرویس داده بازار (یا مستقیماً در پایگاه داده)
                            await self._market_data_service.store_normalized_data_async(local_instrument, self.subscription_type, normalized_data)

                            # 6. ارسال به MessageBus (اگر سیستم پیام‌رسانی وجود داشته باشد)
                            # await self.message_bus.publish(f"market_data.{local_instrument.symbol}.{self.subscription_type}", normalized_data)

                        except Exception as e:
                            logger.error(f"[{self.name}] Error processing WebSocket message from {exchange_name}: {str(e)}")
                            # ادامه یا خروج؟ این بستگی به شدت خطا دارد.
                            # برای این مثال، ادامه می‌دهیم.
                            continue
            except websockets.exceptions.ConnectionClosed as e:
                logger.warning(f"[{self.name}] Connection to {exchange_name} closed: {e.code} - {e.reason}. Attempting to reconnect in {self.ws_reconnect_delay}s...")
                await asyncio.sleep(self.ws_reconnect_delay)
            except Exception as e:
                logger.error(f"[{self.name}] Unexpected error in WebSocket listener for {exchange_name}: {str(e)}. Reconnecting in {self.ws_reconnect_delay}s...")
                await asyncio.sleep(self.ws_reconnect_delay) # تلاش مجدد پس از مدت زمان مشخص

    async def _run_polling_loop(self):
        """
        Polls the exchange API periodically for data (e.g., ticker, OHLCV).
        Less efficient than WebSocket but sometimes necessary.
        """
        logger.info(f"Starting polling loop for {self.name} with interval {self.polling_interval}s.")
        while not self._stop_event.is_set():
            try:
                for instrument in self._instrument_objects:
                    try:
                        # 1. یافتن InstrumentExchangeMap فعال
                        exchange_map = await InstrumentExchangeMap.objects.select_related('exchange').aget(
                            instrument=instrument,
                            is_active=True
                        )
                        exchange_name = exchange_map.exchange.name
                        exchange_symbol = exchange_map.exchange_symbol

                        # 2. استفاده از کانکتور برای گرفتن داده
                        connector = self._connector_service.get_connector(exchange_name)
                        raw_data = await connector.fetch_ticker_data_async(exchange_symbol) # یا تابع مربوط به نوع اشتراک

                        # 3. نرمالایز و ذخیره
                        if raw_data:
                            normalized_data = connector.normalize_data(raw_data, self.subscription_type)
                            await self._market_data_service.store_normalized_data_async(instrument, self.subscription_type, normalized_data)
                            logger.debug(f"Polled data for {instrument.symbol} from {exchange_name}.")

                    except InstrumentExchangeMap.DoesNotExist:
                        logger.warning(f"No active exchange map for {instrument.symbol}. Skipping poll.")
                        continue
                    except Exception as e:
                        logger.error(f"Error polling data for {instrument.symbol}: {str(e)}")
                        # ادامه به نماد بعدی

                # 4. تأخیر قبل از چرخه بعدی
                await asyncio.sleep(self.polling_interval)

            except asyncio.CancelledError:
                logger.info(f"Polling loop for {self.name} was cancelled.")
                break # خروج از حلقه
            except Exception as e:
                logger.error(f"Critical error in polling loop for {self.name}: {str(e)}")
                # ممکن است بخواهید کمی تأخیر کنید قبل از ادامه یا خروج
                await asyncio.sleep(self.polling_interval) # یا مقدار دیگری


    async def shutdown(self):
        """
        Performs cleanup tasks before the agent stops.
        """
        logger.info(f"Shutting down {self.name} agent.")
        # بستن اتصالات WebSocket
        for ws in self._active_ws_connections.values():
            if not ws.closed:
                await ws.close()
        self._active_ws_connections.clear()
        logger.info(f"{self.name} agent shutdown complete.")


# --- سایر عامل‌های مرتبط با ابزار ---
# مثلاً یک عامل برای مدیریت تغییرات در لیست نمادها یا یک عامل برای اعتبارسنجی داده
class InstrumentMonitorAgent(BaseAgent):
    """
    Agent responsible for monitoring changes in instrument definitions (e.g., tick size, lot size, status)
    across different exchanges and updating the local database accordingly.
    Represents a part of the "Product/Monitoring Agent" or "Data Preprocessing Agent" concept.
    """
    def __init__(self, agent_config: Dict[str, Any]):
        super().__init__(agent_config)
        self.name = agent_config.get("name", "InstrumentMonitor")
        self.check_interval_hours = agent_config.get("check_interval_hours", 24) # چک کردن هر 24 ساعت
        self._connector_service = ConnectorService()

    async def run(self):
        logger.info(f"Starting {self.name} agent's monitoring loop.")
        while not self._stop_event.is_set():
            try:
                await self._sync_instrument_details()
                # تأخیر تا زمان چک بعدی
                delay_seconds = self.check_interval_hours * 3600
                await asyncio.sleep(delay_seconds)
            except asyncio.CancelledError:
                logger.info(f"{self.name} agent monitoring loop was cancelled.")
                break
            except Exception as e:
                logger.error(f"Error in {self.name} monitoring loop: {str(e)}")
                # ممکن است بخواهید کمی تأخیر کنید قبل از تلاش مجدد
                await asyncio.sleep(60) # 1 minute before retrying

    async def _sync_instrument_details(self):
        """
        Fetches the latest instrument details from exchanges and updates local mappings.
        """
        logger.info(f"{self.name} starting instrument detail sync.")
        try:
            # 1. گرفتن تمام InstrumentExchangeMapهای فعال
            active_maps = InstrumentExchangeMap.objects.select_related('instrument', 'exchange').filter(is_active=True)

            for map_obj in active_maps:
                exchange_name = map_obj.exchange.name
                exchange_symbol = map_obj.exchange_symbol

                try:
                    # 2. گرفتن اطلاعات از صرافی
                    connector = self._connector_service.get_connector(exchange_name)
                    raw_details = await connector.fetch_instrument_details_async(exchange_symbol)

                    # 3. بروزرسانی فیلدهای مرتبط در InstrumentExchangeMap
                    updated_fields = {}
                    # مثلاً:
                    if 'tickSize' in raw_details:
                        new_tick_size = Decimal(str(raw_details['tickSize']))
                        if map_obj.tick_size != new_tick_size:
                            updated_fields['tick_size'] = new_tick_size
                    if 'lotSize' in raw_details:
                        new_lot_size = Decimal(str(raw_details['lotSize']))
                        if map_obj.lot_size != new_lot_size:
                            updated_fields['lot_size'] = new_lot_size
                    if 'status' in raw_details:
                        is_active_on_exchange = raw_details['status'] == 'TRADING'
                        if map_obj.is_active != is_active_on_exchange:
                            updated_fields['is_active'] = is_active_on_exchange
                    # ... سایر فیلدها

                    if updated_fields:
                        await InstrumentExchangeMap.objects.filter(id=map_obj.id).aupdate(**updated_fields)
                        logger.info(f"Updated details for {map_obj.instrument.symbol} on {exchange_name} based on exchange data.")

                except Exception as e:
                    logger.error(f"Failed to sync details for {exchange_symbol} on {exchange_name}: {str(e)}")
                    # ادامه به نماد بعدی

        except Exception as e:
            logger.error(f"Critical error during instrument detail sync in {self.name}: {str(e)}")
            # مدیریت خطا مناسب


    async def shutdown(self):
        logger.info(f"Shutting down {self.name} agent.")
        # کارهای پایانی
        logger.info(f"{self.name} agent shutdown complete.")

# --- عامل مدیریت لیست نظارتی ---
class InstrumentWatchlistAgent(BaseAgent):
    """
    Agent responsible for managing and reacting to changes in user-defined instrument watchlists.
    It can trigger specific actions (e.g., sending alerts, running scans) when instruments in a watchlist meet certain criteria.
    Represents a simplified version of logic that might be handled by a more complex "Strategy" or "Alerting" agent.
    """
    def __init__(self, agent_config: Dict[str, Any]):
        super().__init__(agent_config)
        self.name = agent_config.get("name", "InstrumentWatchlistAgent")
        self.scan_interval_minutes = agent_config.get("scan_interval_minutes", 5) # چک کردن هر 5 دقیقه
        self._market_data_service = MarketDataService()

    async def run(self):
        logger.info(f"Starting {self.name} agent's watchlist scan loop.")
        while not self._stop_event.is_set():
            try:
                await self._scan_watchlists()
                delay_seconds = self.scan_interval_minutes * 60
                await asyncio.sleep(delay_seconds)
            except asyncio.CancelledError:
                logger.info(f"{self.name} agent scan loop was cancelled.")
                break
            except Exception as e:
                logger.error(f"Error in {self.name} scan loop: {str(e)}")
                await asyncio.sleep(60) # تأخیر قبل از تلاش مجدد

    async def _scan_watchlists(self):
        """
        Scans active watchlists and performs actions based on criteria.
        This is a simplified example. Real logic could be much more complex.
        """
        from .models import InstrumentWatchlist # ایمپورت درون تابع برای جلوگیری از حلقه
        logger.debug(f"{self.name} scanning watchlists.")
        try:
            # 1. گرفتن تمام لیست‌های نظارتی فعال (یا آنهایی که نیاز به اسکن دارند)
            watchlists = await InstrumentWatchlist.objects.prefetch_related('instruments').filter(is_active=True).aiterator()

            async for watchlist in watchlists:
                logger.debug(f"Scanning watchlist: {watchlist.name}")
                instruments = watchlist.instruments.all()
                for instrument in instruments:
                    # 2. گرفتن آخرین داده (مثلاً قیمت بسته شدن 1m قبل)
                    latest_snapshot = await self._market_data_service.get_latest_snapshot_async(instrument, timeframe='1m')
                    if latest_snapshot:
                        current_price = latest_snapshot.close_price
                        # 3. منطق ساده: اگر قیمت بیش از 2% از آخرین قیمت مرجع بالاتر رفت، اعلام کن
                        # (این باید با منطق پیچیده‌تر و ذخیره قیمت مرجع قبلی جایگزین شود)
                        # ... محاسبات و تصمیم‌گیری ...
                        # 4. ارسال اعلان یا انجام عمل (مثلاً فعال‌سازی یک عامل معاملاتی)
                        # await self._trigger_action(watchlist, instrument, current_price)

        except Exception as e:
            logger.error(f"Error scanning watchlists in {self.name}: {str(e)}")

    async def shutdown(self):
        logger.info(f"Shutting down {self.name} agent.")
        logger.info(f"{self.name} agent shutdown complete.")

# --- سایر عامل‌های ممکن ---
# - عامل تحلیل الگوی اکشن قیمت (Price Action Pattern Analysis Agent)
# - عامل کشف مفهوم اسمارت مانی (Smart Money Concept Discovery Agent)
# - عامل ارزیابی متریک‌های هوش مصنوعی (AI Metric Evaluator Agent)
# این عامل‌ها می‌توانند از سرویس‌های موجود در apps.analysis یا apps.ai استفاده کنند و با این اپلیکیشن تعامل داشته باشند.
