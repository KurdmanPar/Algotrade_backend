# tests/test_accounts/test_tasks.py

import pytest
from django.core import mail
from django.utils import timezone
from apps.accounts.models import CustomUser, UserProfile, UserSession, UserAPIKey
from apps.accounts.tasks import (
    send_verification_email_task,
    send_password_reset_email_task,
    send_2fa_codes_task,
    deactivate_user_session_task,
    revoke_api_key_task,
    cleanup_expired_sessions_task,
    cleanup_expired_api_keys_task,
    send_security_alert_task,
)
from unittest.mock import patch

pytestmark = pytest.mark.django_db

class TestAccountTasks:
    """
    Test suite for the Celery tasks in accounts app.
    Note: These tests often mock external dependencies like email sending or service calls.
    """

    @patch('apps.accounts.tasks.EmailMultiAlternatives.send')
    def test_send_verification_email_task(self, mock_send, CustomUserFactory):
        """Test the send_verification_email_task."""
        user = CustomUserFactory(email='test@example.com')
        token = 'test-token'

        send_verification_email_task(user.id, token)

        assert len(mail.outbox) == 1
        sent_email = mail.outbox[0]
        assert 'Verify your email address' in sent_email.subject
        assert user.email in sent_email.to
        # Verify the token is included in the URL (mocking URL generation might be needed for full check)
        mock_send.assert_called_once()

    @patch('apps.accounts.tasks.EmailMultiAlternatives.send')
    def test_send_password_reset_email_task(self, mock_send, CustomUserFactory):
        """Test the send_password_reset_email_task."""
        user = CustomUserFactory(email='test@example.com')
        token = 'reset-token'

        send_password_reset_email_task(user.id, token)

        assert len(mail.outbox) == 1
        sent_email = mail.outbox[0]
        assert 'Reset your password' in sent_email.subject
        assert user.email in sent_email.to
        mock_send.assert_called_once()

    @patch('apps.accounts.tasks.EmailMultiAlternatives.send')
    def test_send_2fa_codes_task(self, mock_send, CustomUserFactory):
        """Test the send_2fa_codes_task."""
        user = CustomUserFactory(email='test@example.com')
        codes = ['CODE1234', 'CODE5678']

        send_2fa_codes_task(user.id, codes)

        assert len(mail.outbox) == 1
        sent_email = mail.outbox[0]
        assert 'Two-Factor Authentication Backup Codes' in sent_email.subject
        assert user.email in sent_email.to
        # Verify codes are in the body
        assert 'CODE1234' in sent_email.body
        mock_send.assert_called_once()

    def test_deactivate_user_session_task(self, UserSessionFactory):
        """Test the deactivate_user_session_task."""
        session = UserSessionFactory(is_active=True)
        user = session.user
        session_key = session.session_key

        deactivate_user_session_task(user.id, session_key)

        session.refresh_from_db()
        assert session.is_active is False

    def test_revoke_api_key_task(self, UserAPIKeyFactory):
        """Test the revoke_api_key_task."""
        api_key = UserAPIKeyFactory(is_active=True)
        user = api_key.user
        api_key_id = api_key.id

        revoke_api_key_task(user.id, api_key_id)

        api_key.refresh_from_db()
        assert api_key.is_active is False

    def test_cleanup_expired_sessions_task(self, UserSessionFactory):
        """Test the cleanup_expired_sessions_task."""
        # Create an expired session
        expired_session = UserSessionFactory(
            is_active=True,
            expires_at=timezone.now() - timezone.timedelta(days=1)
        )
        # Create an active session
        active_session = UserSessionFactory(
            is_active=True,
            expires_at=timezone.now() + timezone.timedelta(days=1)
        )

        cleanup_expired_sessions_task()

        expired_session.refresh_from_db()
        active_session.refresh_from_db()
        assert expired_session.is_active is False
        assert active_session.is_active is True

    def test_cleanup_expired_api_keys_task(self, UserAPIKeyFactory):
        """Test the cleanup_expired_api_keys_task."""
        # Create an expired API key
        expired_key = UserAPIKeyFactory(
            is_active=True,
            expires_at=timezone.now() - timezone.timedelta(days=1)
        )
        # Create an active API key
        active_key = UserAPIKeyFactory(
            is_active=True,
            expires_at=timezone.now() + timezone.timedelta(days=1)
        )

        cleanup_expired_api_keys_task()

        expired_key.refresh_from_db()
        active_key.refresh_from_db()
        assert expired_key.is_active is False
        assert active_key.is_active is True

    @patch('apps.accounts.tasks.EmailMultiAlternatives.send')
    def test_send_security_alert_task(self, mock_send, CustomUserFactory):
        """Test the send_security_alert_task."""
        user = CustomUserFactory(email='test@example.com')
        alert_message = 'Suspicious activity detected.'

        send_security_alert_task(user.id, alert_message)

        assert len(mail.outbox) == 1
        sent_email = mail.outbox[0]
        assert 'Security Alert' in sent_email.subject
        assert user.email in sent_email.to
        assert alert_message in sent_email.body
        mock_send.assert_called_once()
