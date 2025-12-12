# apps/market_data/agents.py
import asyncio
import json
import logging
import ssl
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
from django.conf import settings
from django.utils import timezone
import websockets
import aiohttp
from apps.agents.models import Agent, AgentStatus, AgentMessage, AgentLog, AgentMetric
from apps.market_data.models import DataSource, MarketDataConfig, MarketDataSnapshot, MarketDataSyncLog
from apps.instruments.models import Instrument
from apps.connectors.models import APICredential
from apps.core.messaging import MessageBus  # فرض می‌کنیم یک کلاس یکپارچه برای پیام‌رسانی دارید

logger = logging.getLogger(__name__)


class MarketDataAgent:
    """
    عامل اصلی جمع‌آوری داده بازار.
    - قابلیت اتصال به چندین صرافی.
    - استفاده از الگوی آداپتور برای کانکتورها.
    - پشتیبانی از WebSocket و REST.
    - ذخیره داده در PostgreSQL/TimescaleDB.
    - ارسال داده به سایر عامل‌ها از طریق MessageBus.
    - مدیریت اشتراک‌ها و محدودیت‌های نرخ.
    - امنیت (رمزنگاری، اعتبارسنجی، لاگ).
    """
    def __init__(self, agent_model_id: int):
        self.agent_model: Agent = Agent.objects.select_related(
            'agent_type', 'owner'
        ).prefetch_related('config').get(id=agent_model_id)

        self.config = self.agent_model.config.params  # مثلاً {'symbols': ['BTCUSDT'], 'timeframes': ['1m'], 'sources': ['BINANCE']}
        self.is_running = False
        self.status: AgentStatus = self.agent_model.status
        self.message_bus = MessageBus()
        self.active_websockets = {}  # {config_id: websocket_connection}
        self.rate_limit_buckets = {}  # {source_id: {'count': int, 'reset_time': datetime}}
        self.subscriptions = set()  # {(instrument_id, source_id, timeframe, data_type)}

    def start(self):
        logger.info(f"MarketDataAgent {self.agent_model.name} started.")
        self.is_running = True
        self.status.state = "RUNNING"
        self.status.save()
        asyncio.run(self._run_main_loop())

    def stop(self):
        logger.info(f"MarketDataAgent {self.agent_model.name} stopped.")
        self.is_running = False
        self.status.state = "STOPPED"
        self.status.save()
        # بستن تمام اتصالات WebSocket
        for ws in self.active_websockets.values():
            if not ws.closed:
                ws.close()

    async def _run_main_loop(self):
        """
        حلقه اصلی: بارگذاری کانفیگ، اتصال، دریافت، نرمالایز، ذخیره، ارسال.
        """
        # 1. بارگذاری تمام کانفیگ‌های فعال
        configs = MarketDataConfig.objects.filter(
            status='PENDING'
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
            # 3. برای REST می‌توانید تسک‌های دوره‌ای (cron-like) ایجاد کنید یا در صورت نیاز فراخوانی کنید.

    async def _run_websocket_stream(self, config: MarketDataConfig):
        """
        اتصال به WebSocket یک منبع داده و شروع دریافت داده.
        """
        connector_class = self._get_connector_class(config.data_source.name)
        if not connector_class:
            logger.error(f"No connector found for source: {config.data_source.name}")
            self._log_agent_message(f"No connector found for {config.data_source.name}", level="ERROR")
            return

        connector = connector_class(
            config=config,
            credential=config.api_credential,
            agent=self
        )

        while self.is_running:
            try:
                await connector.connect()
                logger.info(f"Connected to {config.data_source.name} for {config.instrument.symbol}")
                async for message in connector.listen():
                    await self._process_raw_message(message, config)

            except websockets.exceptions.ConnectionClosed:
                logger.warning(f"WebSocket to {config.data_source.name} closed. Reconnecting...")
                await asyncio.sleep(5)  # exponential backoff
            except Exception as e:
                logger.error(f"Error in WebSocket stream for {config}: {e}")
                self._log_agent_message(str(e), level="ERROR")
                await asyncio.sleep(10)

    async def _process_raw_message(self, raw_data: Dict[str, Any], config: MarketDataConfig):
        """
        پردازش یک پیام خام از WebSocket و تبدیل، ذخیره و ارسال آن.
        """
        try:
            # 1. نرمالایز کردن داده
            normalized_data = self._normalize_data(raw_data, config.data_source.name, config.data_type)

            # 2. ذخیره در دیتابیس
            snapshot = MarketDataSnapshot.objects.create(
                config=config,
                timestamp=timezone.make_aware(datetime.fromtimestamp(normalized_data['timestamp'])),
                open_price=normalized_data['open'],
                high_price=normalized_data['high'],
                low_price=normalized_data['low'],
                close_price=normalized_data['close'],
                volume=normalized_data['volume'],
                best_bid=normalized_data.get('best_bid'),
                best_ask=normalized_data.get('best_ask'),
                bid_size=normalized_data.get('bid_size'),
                ask_size=normalized_data.get('ask_size'),
                additional_data=normalized_data.get('additional_data', {})
            )

            # 3. ارسال به سایر عامل‌ها از طریق MessageBus
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
                "source": config.data_source.name,
            }
            await self.message_bus.publish(topic, payload)

            # 4. لاگ و متریک
            self._log_agent_message(f"Stored and published snapshot for {config.instrument.symbol}", level="INFO")
            self._update_metrics(config.instrument.symbol)

        except Exception as e:
            logger.error(f"Error processing message for {config}: {e}")
            self._log_agent_message(f"Error processing message: {e}", level="ERROR")

    def _normalize_data(self, raw_data: Dict[str, Any], source_name: str, data_type: str) -> Dict[str, Any]:
        """
        تبدیل داده خام از هر صرافی به یک فرمت یکنواخت.
        این تابع باید بر اساس source_name و data_type منطق متفاوتی داشته باشد.
        """
        # مثال ساده برای OHLCV
        if data_type == 'OHLCV':
            # نگاشت فیلدها از هر صرافی به فرمت استاندارد
            if source_name.upper() == 'BINANCE':
                return {
                    "timestamp": raw_data['k']['T'],
                    "open": Decimal(raw_data['k']['o']),
                    "high": Decimal(raw_data['k']['h']),
                    "low": Decimal(raw_data['k']['l']),
                    "close": Decimal(raw_data['k']['c']),
                    "volume": Decimal(raw_data['k']['v']),
                }
            elif source_name.upper() == 'NOBITEX':
                # منطق نرمالایز Nobitex
                return {
                    "timestamp": raw_data['t'],
                    "open": Decimal(raw_data['o']),
                    "high": Decimal(raw_data['h']),
                    "low": Decimal(raw_data['l']),
                    "close": Decimal(raw_data['c']),
                    "volume": Decimal(raw_data['v']),
                }
            # ... سایر صرافی‌ها

        elif data_type == 'TICK':
            # منطق برای TICK
            pass

        return raw_data # اگر نرمالایز نشد، همان داده را برگردان

    def _get_connector_class(self, source_name: str):
        """
        بازیابی کلاس کانکتور مربوط به یک منبع داده.
        اینجا می‌توانید از الگوی Registry استفاده کنید.
        """
        from apps.connectors.registry import get_connector
        return get_connector(source_name.upper())

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
        # AgentMetric.objects.update_or_create(...)
        pass