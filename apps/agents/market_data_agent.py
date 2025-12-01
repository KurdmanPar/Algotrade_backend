# apps/agents/market_data_agent.py
import asyncio
import json
import logging
import ssl
import websockets
import aiohttp
from decimal import Decimal
from datetime import datetime
from django.utils import timezone
from apps.agents.models import Agent, AgentStatus, AgentMessage, AgentLog, AgentMetric
from apps.market_data.models import DataSource, MarketDataConfig, MarketDataSnapshot
from apps.instruments.models import Instrument
from apps.connectors.models import APICredential
from apps.core.messaging import MessageBus  # فرض بر این است که این کلاس وجود دارد

logger = logging.getLogger(__name__)


class MarketDataAgent:
    """
    عامل جمع‌آوری داده بازار.
    - اتصال به WebSocket یا REST API صرافی‌ها
    - دریافت داده OHLCV، OrderBook، Ticks
    - ذخیره در دیتابیس (PostgreSQL یا MongoDB)
    - ارسال به سایر عامل‌ها از طریق MessageBus
    - مدیریت اشتراک‌ها، محدودیت نرخ، خطاهای اتصال
    """
    def __init__(self, agent_model_id: int):
        self.agent_model = Agent.objects.select_related(
            'agent_type', 'owner'
        ).prefetch_related('config').get(id=agent_model_id)

        self.config = self.agent_model.config.params  # مثلاً شامل symbols, timeframe, exchange_code
        self.status = self.agent_model.status
        self.is_running = False
        self.message_bus = MessageBus()
        self.active_websockets = {}  # {config_id: websocket_connection}
        self.subscriptions = set()  # {(instrument_id, source_id, timeframe, data_type)}
        self.rate_limit_buckets = {}  # {source_id: {'count': int, 'reset_time': datetime}}

    def start(self):
        """
        شروع حلقه اصلی گرفتن داده.
        """
        logger.info(f"MarketDataAgent {self.agent_model.name} started.")
        self.is_running = True
        self.status.state = "RUNNING"
        self.status.save()
        # اجرای حلقه اصلی در asyncio
        asyncio.run(self._run_loop())

    def stop(self):
        """
        توقف عامل.
        """
        logger.info(f"MarketDataAgent {self.agent_model.name} stopped.")
        self.is_running = False
        self.status.state = "STOPPED"
        self.status.save()
        # بستن تمام اتصالات WebSocket
        for ws in self.active_websockets.values():
            if not ws.closed:
                ws.close()

    async def _run_loop(self):
        """
        حلقه اصلی عامل: بارگذاری کانفیگ، اتصال، دریافت داده، پردازش و ذخیره.
        """
        # 1. بارگذاری تمام کانفیگ‌های فعال
        configs = MarketDataConfig.objects.filter(
            is_active=True,
            is_realtime=True  # فقط داده‌های لحظه‌ای
        ).select_related('instrument', 'data_source', 'api_credential')

        for config in configs:
            self.subscriptions.add((
                config.instrument_id,
                config.data_source_id,
                config.timeframe,
                config.data_type
            ))
            if config.data_source.type == 'WEBSOCKET':
                # 2. برای کانکتورهای WebSocket، یک تسک ایجاد کن
                asyncio.create_task(self._run_websocket_stream(config))

    async def _run_websocket_stream(self, config: MarketDataConfig):
        """
        اتصال به WebSocket یک منبع داده و شروع دریافت داده.
        """
        # پیدا کردن کلاس کانکتور از طریق registry
        from apps.connectors.registry import get_connector
        connector_class = get_connector(config.data_source.code.upper())  # مثلاً 'BINANCE'
        if not connector_class:
            logger.error(f"No connector found for source: {config.data_source.code}")
            self._log_agent_message(f"No connector found for {config.data_source.code}", level="ERROR")
            return

        credential = config.api_credential
        api_key = credential.api_key_encrypted if credential else ""
        api_secret = credential.api_secret_encrypted if credential else ""

        connector = connector_class(
            api_key=api_key,
            api_secret=api_secret,
            config=config,
            agent=self
        )

        while self.is_running:
            try:
                await connector.connect()
                logger.info(f"Connected to {config.data_source.code} for {config.instrument.symbol}")
                # اشتراک در کانال مربوطه
                await connector.subscribe_to_instrument(config.instrument.symbol, config.timeframe)
                async for message in connector.listen():
                    await self._process_message(message, config)

            except websockets.exceptions.ConnectionClosed:
                logger.warning(f"WebSocket to {config.data_source.code} closed. Reconnecting...")
                await asyncio.sleep(5)  # exponential backoff
            except Exception as e:
                logger.error(f"Error in WebSocket stream for {config}: {e}")
                self._log_agent_message(str(e), level="ERROR")
                await asyncio.sleep(10)

    async def _process_message(self, raw_data: dict, config: MarketDataConfig):
        """
        پردازش یک پیام دریافتی از WebSocket و ذخیره در دیتابیس.
        """
        try:
            # 1. نرمالایز کردن داده (تبدیل به فرمت یکنواخت)
            normalized_data = self._normalize_data(raw_data, config.data_source.code, config.data_type)

            # 2. ذخیره در دیتابیس
            snapshot = MarketDataSnapshot.objects.create(
                config=config,
                timestamp=timezone.make_aware(datetime.fromtimestamp(normalized_data['timestamp'])),
                open_price=Decimal(str(normalized_data['open'])),
                high_price=Decimal(str(normalized_data['high'])),
                low_price=Decimal(str(normalized_data['low'])),
                close_price=Decimal(str(normalized_data['close'])),
                volume=Decimal(str(normalized_data['volume'])),
                best_bid=Decimal(str(normalized_data.get('best_bid', 0))),
                best_ask=Decimal(str(normalized_data.get('best_ask', 0))),
                bid_size=Decimal(str(normalized_data.get('bid_size', 0))),
                ask_size=Decimal(str(normalized_data.get('ask_size', 0))),
                additional_data=normalized_data.get('additional_data', {})
            )
            logger.info(f"Stored snapshot for {config.instrument.symbol} at {snapshot.timestamp}")

            # 3. ارسال داده به سایر عامل‌ها (مثل StrategyAgent) از طریق MessageBus
            topic = f"market.{config.instrument.symbol}.{config.timeframe}"
            payload = {
                "instrument_id": config.instrument.id,
                "symbol": config.instrument.symbol,
                "timestamp": snapshot.timestamp.isoformat(),
                "open": float(snapshot.open_price),
                "high": float(snapshot.high_price),
                "low": float(snapshot.low_price),
                "close": float(snapshot.close_price),
                "volume": float(snapshot.volume),
                "source": config.data_source.code,
            }
            await self.message_bus.publish(topic, payload)

            # 4. به‌روزرسانی متریک‌ها
            self._update_metrics(config.instrument.symbol)

        except Exception as e:
            logger.error(f"Error processing message for {config}: {e}")
            self._log_agent_message(f"Error processing message: {e}", level="ERROR")

    def _normalize_data(self, raw_data: dict, source_code: str, data_type: str) -> dict:
        """
        تبدیل داده خام از هر صرافی به یک فرمت یکنواخت.
        """
        # مثال ساده برای OHLCV
        if data_type == 'OHLCV':
            if source_code.upper() == 'BINANCE':
                return {
                    "timestamp": raw_data['k']['T'],
                    "open": raw_data['k']['o'],
                    "high": raw_data['k']['h'],
                    "low": raw_data['k']['l'],
                    "close": raw_data['k']['c'],
                    "volume": raw_data['k']['v'],
                    "best_bid": raw_data.get('b', 0),
                    "best_ask": raw_data.get('a', 0),
                }
            elif source_code.upper() == 'NOBITEX':
                # منطق نرمالایز Nobitex
                return {
                    "timestamp": raw_data['timestamp'],
                    "open": raw_data['open'],
                    "high": raw_data['high'],
                    "low": raw_data['low'],
                    "close": raw_data['close'],
                    "volume": raw_data['volume'],
                }
            # سایر صرافی‌ها...
        return raw_data

    def _log_agent_message(self, message: str, level: str = "INFO"):
        AgentLog.objects.create(
            agent=self.agent_model,
            level=level,
            message=message,
            extra_data={"source": "MarketDataAgent"},
        )

    def _update_metrics(self, symbol: str):
        # مثلاً افزایش تعداد پیام دریافتی
        # باید یک مدل AgentMetric داشته باشید
        from django.utils import timezone
        AgentMetric.objects.update_or_create(
            agent=self.agent_model,
            period_start=timezone.now().replace(minute=0, second=0, microsecond=0),
            defaults={
                'messages_received': models.F('messages_received') + 1
            }
        )