# tests/test_core/test_messaging.py

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from apps.core.messaging import MessageBus, BaseAgent
from apps.core.models import AuditLog
from apps.accounts.factories import CustomUserFactory
from apps.instruments.factories import InstrumentFactory
from apps.bots.factories import TradingBotFactory # فرض بر این است که وجود دارد

pytestmark = pytest.mark.django_db

class TestMessageBus:
    """
    Tests for the MessageBus class.
    """
    @pytest.fixture
    def mock_redis_client(self, mocker):
        """
        Fixture to mock the redis client used by MessageBus.
        """
        mock_redis_lib = mocker.patch('apps.core.messaging.redis')
        mock_instance = MagicMock()
        mock_redis_lib.Redis.return_value = mock_instance
        return mock_instance

    @pytest.fixture
    def message_bus(self, mock_redis_client):
        """
        Fixture to create a MessageBus instance with mocked broker.
        """
        mb = MessageBus(broker_type='redis')
        mb._broker_instance = mock_redis_client
        return mb

    def test_message_bus_initialization_with_redis(self, mocker):
        """
        Test that the MessageBus initializes the correct broker (Redis).
        """
        mock_redis_lib = mocker.patch('apps.core.messaging.redis')
        mock_redis_instance = MagicMock()
        mock_redis_lib.Redis.return_value = mock_redis_instance

        mb = MessageBus(broker_type='redis')

        mock_redis_lib.Redis.assert_called_once()
        # اطمینان از اینکه _broker_instance به نمونه صحیح اشاره دارد
        assert mb._broker_instance == mock_redis_instance

    def test_message_bus_initialization_with_unsupported_broker(self):
        """
        Test that the MessageBus raises an error for unsupported broker types.
        """
        with pytest.raises(ValueError, match="Unsupported broker type: kafka"):
            MessageBus(broker_type='kafka')

    def test_publish_to_redis(self, message_bus, mock_redis_client):
        """
        Test publishing a message to Redis.
        """
        topic = 'test_topic'
        message = {'event': 'test_event', 'data': 'test_data'}
        sender_id = 'test_sender_123'

        message_bus.publish(topic, message, sender_id=sender_id)

        # چک کردن فراخوانی publish در نمونه Redis
        mock_redis_client.publish.assert_called_once()
        call_args = mock_redis_client.publish.call_args
        assert call_args[0][0] == topic # اولین آرگومان topic است
        # دومین آرگومان باید JSON string شده envelope باشد
        import json
        sent_envelope_str = call_args[0][1]
        sent_envelope = json.loads(sent_envelope_str)
        assert sent_envelope['topic'] == topic
        assert sent_envelope['message'] == message
        assert sent_envelope['sender_id'] == sender_id
        assert 'timestamp' in sent_envelope # فرض: زمان در envelope اضافه می‌شود

    def test_broadcast_to_redis(self, message_bus, mock_redis_client):
        """
        Test broadcasting a message to all connected agents via Redis.
        """
        message = {'event': 'broadcast_event', 'data': 'broadcast_data'}
        sender_id = 'broadcaster_123'
        exclude_list = ['exclude_agent_1']

        message_bus.broadcast(message, sender_id=sender_id, exclude_senders=exclude_list)

        # چک کردن فراخوانی publish در نمونه Redis برای کانال 'broadcast'
        mock_redis_client.publish.assert_called_once()
        call_args = mock_redis_client.publish.call_args
        assert call_args[0][0] == 'broadcast' # topic باید broadcast باشد
        import json
        sent_envelope_str = call_args[0][1]
        sent_envelope = json.loads(sent_envelope_str)
        assert sent_envelope['message'] == message
        assert sent_envelope['sender_id'] == sender_id
        # assert sent_envelope['exclude_list'] == exclude_list # این فیلد ممکن است در envelope نباشد و فقط در منطق publish استفاده شود


class TestBaseAgent:
    """
    Tests for the BaseAgent class.
    """
    @pytest.fixture
    def mock_message_bus(self, mocker):
        """
        Fixture to mock the MessageBus instance used by the agent.
        """
        mock_bus = MagicMock()
        return mock_bus

    @pytest.fixture
    def base_agent(self, mock_message_bus):
        """
        Fixture to create a BaseAgent instance with mocked dependencies.
        """
        agent_config = {
            'id': 'test_agent_1',
            'name': 'Test Agent',
            'type': 'data_collector',
            'owner_id': 1,
            'config': {'param1': 'value1'}
        }
        agent = BaseAgent(agent_config=agent_config, message_bus=mock_message_bus)
        return agent

    def test_base_agent_initialization(self, base_agent, mock_message_bus):
        """
        Test that the BaseAgent initializes correctly with config and message bus.
        """
        assert base_agent.agent_config['id'] == 'test_agent_1'
        assert base_agent.message_bus == mock_message_bus
        assert base_agent.agent_id == 'test_agent_1'
        assert base_agent.is_running is False

    def test_base_agent_subscribe_to_channel(self, base_agent, mock_message_bus):
        """
        Test that the agent can subscribe to a channel via the message bus.
        """
        handler_mock = MagicMock()
        channel_name = 'agent_orders_test_agent_1'

        base_agent.subscribe_to_channel(channel_name, handler_mock)

        # چک کردن اینکه متد subscribe از message bus فراخوانی شده است
        mock_message_bus.subscribe.assert_called_once_with(channel_name, handler_mock)

    def test_base_agent_publish_message(self, base_agent, mock_message_bus):
        """
        Test that the agent can publish a message via the message bus.
        """
        message = {'alert': 'Risk threshold exceeded', 'level': 'HIGH'}
        topic = 'risk_alerts'

        base_agent.publish_message(topic, message)

        # چک کردن اینکه متد publish از message bus با ID عامل فراخوانی شده است
        mock_message_bus.publish.assert_called_once_with(topic, message, sender_id='test_agent_1')

    def test_base_agent_log_event(self, base_agent, caplog):
        """
        Test that the agent can log events.
        """
        message = "This is a test log message."
        level = "INFO"

        with caplog.at_level(level):
            base_agent.log_event(message, level)

        assert message in caplog.text
        assert level in caplog.text

    def test_base_agent_audit_log_event(self, base_agent, mock_message_bus, mocker):
        """
        Test that the agent can trigger audit logging.
        """
        mock_audit_service_log = mocker.patch('apps.core.services.AuditService.log_event') # فرض: AuditService وجود دارد
        # اگر agent_config شامل owner_id بود
        user_id = base_agent.agent_config['owner_id']
        # فرض: گرفتن کاربر از پایگاه داده
        from apps.accounts.models import CustomUser
        mock_user = MagicMock(spec=CustomUser)
        mock_user.id = user_id
        # ممکن است نیاز به mock کردن get_user_model یا CustomUser.objects.get باشد
        # mocker.patch('apps.accounts.models.CustomUser.objects.get', return_value=mock_user)

        action = 'AGENT_STARTED'
        target_model = 'TradingAgent'
        target_id = 'some_id'
        details = {'config': base_agent.agent_config}

        base_agent.audit_log_event(action, target_model, target_id, details)

        # چک کردن فراخوانی سرویس حسابرسی
        mock_audit_service_log.assert_called_once_with(
            user=mock_user, # کاربر با استفاده از owner_id گرفته می‌شود (mock شده است)
            action=action,
            target_model_name=target_model,
            target_id=target_id,
            details=details,
            request=None # چون در محیط Agent مستقیماً request نداریم
        )

    # --- تست متدهای کمکی BaseAgent ---
    # def test_base_agent_some_utility_method(self, base_agent):
    #     # ...

# --- تست سایر اجزای Messaging (اگر وجود داشتند) ---
# می‌توانید تست‌هایی برای کلاس‌های یا توابعی که در messaging.py تعریف می‌کنید بنویسید
# مثلاً اگر کلاس‌هایی برای مدیریت پیام‌های خاص (مثل HeartbeatMessage) وجود داشتند

logger.info("Core messaging tests loaded successfully.")
