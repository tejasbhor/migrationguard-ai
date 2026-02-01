"""
Unit Tests for Alert Manager.

This module tests the alert manager functionality including
alert rule evaluation, notification delivery, and cooldown management.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from migrationguard_ai.services.alert_manager import (
    AlertManager,
    AlertSeverity,
    AlertChannel,
    AlertRule,
)
from migrationguard_ai.services.redis_client import RedisClient


@pytest.fixture
def mock_redis_client():
    """Create mock Redis client."""
    client = AsyncMock(spec=RedisClient)
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock()
    client.delete = AsyncMock()
    return client


@pytest.fixture
def alert_manager(mock_redis_client):
    """Create alert manager instance."""
    return AlertManager(mock_redis_client)


class TestAlertRule:
    """Test AlertRule class."""
    
    def test_alert_rule_creation(self):
        """Test creating an alert rule."""
        rule = AlertRule(
            name="test_rule",
            condition="error_rate > 0.05",
            severity=AlertSeverity.ERROR,
            channels=[AlertChannel.EMAIL, AlertChannel.SLACK],
            cooldown_minutes=15
        )
        
        assert rule.name == "test_rule"
        assert rule.condition == "error_rate > 0.05"
        assert rule.severity == AlertSeverity.ERROR
        assert rule.channels == [AlertChannel.EMAIL, AlertChannel.SLACK]
        assert rule.cooldown_minutes == 15
    
    def test_alert_rule_default_template(self):
        """Test alert rule with default message template."""
        rule = AlertRule(
            name="test_rule",
            condition="test",
            severity=AlertSeverity.INFO,
            channels=[AlertChannel.EMAIL]
        )
        
        assert rule.message_template == "{message}"


class TestAlertManager:
    """Test AlertManager class."""
    
    def test_initialization(self, alert_manager):
        """Test alert manager initialization."""
        assert alert_manager is not None
        assert len(alert_manager.rules) > 0
        assert "high_error_rate" in alert_manager.rules
        assert "confidence_drift" in alert_manager.rules
        assert "critical_error" in alert_manager.rules
    
    def test_default_rules(self, alert_manager):
        """Test default alert rules are properly configured."""
        # Check high_error_rate rule
        rule = alert_manager.rules["high_error_rate"]
        assert rule.severity == AlertSeverity.ERROR
        assert AlertChannel.EMAIL in rule.channels
        assert AlertChannel.SLACK in rule.channels
        
        # Check critical_error rule
        rule = alert_manager.rules["critical_error"]
        assert rule.severity == AlertSeverity.CRITICAL
        assert AlertChannel.PAGERDUTY in rule.channels
    
    @pytest.mark.asyncio
    async def test_is_in_cooldown_false(self, alert_manager, mock_redis_client):
        """Test cooldown check when not in cooldown."""
        mock_redis_client.get.return_value = None
        
        result = await alert_manager._is_in_cooldown("test_rule")
        
        assert result is False
        mock_redis_client.get.assert_called_once_with("alert:cooldown:test_rule")
    
    @pytest.mark.asyncio
    async def test_is_in_cooldown_true(self, alert_manager, mock_redis_client):
        """Test cooldown check when in cooldown."""
        mock_redis_client.get.return_value = "1"
        
        result = await alert_manager._is_in_cooldown("test_rule")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_set_cooldown(self, alert_manager, mock_redis_client):
        """Test setting cooldown period."""
        await alert_manager._set_cooldown("test_rule", 15)
        
        mock_redis_client.set.assert_called_once_with(
            "alert:cooldown:test_rule",
            "1",
            ex=900  # 15 minutes * 60 seconds
        )
    
    @pytest.mark.asyncio
    async def test_clear_cooldown(self, alert_manager, mock_redis_client):
        """Test clearing cooldown."""
        await alert_manager.clear_cooldown("test_rule")
        
        mock_redis_client.delete.assert_called_once_with("alert:cooldown:test_rule")
    
    @pytest.mark.asyncio
    async def test_send_alert_unknown_rule(self, alert_manager):
        """Test sending alert with unknown rule name."""
        result = await alert_manager.send_alert(
            "unknown_rule",
            {"message": "test"}
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_alert_in_cooldown(self, alert_manager, mock_redis_client):
        """Test sending alert when in cooldown."""
        mock_redis_client.get.return_value = "1"  # In cooldown
        
        result = await alert_manager.send_alert(
            "high_error_rate",
            {"error_rate": 0.10}
        )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_alert_override_cooldown(self, alert_manager, mock_redis_client):
        """Test sending alert with cooldown override."""
        mock_redis_client.get.return_value = "1"  # In cooldown
        
        with patch.object(alert_manager, '_send_email_alert', new_callable=AsyncMock):
            with patch.object(alert_manager, '_send_slack_alert', new_callable=AsyncMock):
                result = await alert_manager.send_alert(
                    "high_error_rate",
                    {"error_rate": 0.10},
                    override_cooldown=True
                )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_send_alert_success(self, alert_manager, mock_redis_client):
        """Test successful alert sending."""
        mock_redis_client.get.return_value = None  # Not in cooldown
        
        with patch.object(alert_manager, '_send_email_alert', new_callable=AsyncMock):
            with patch.object(alert_manager, '_send_slack_alert', new_callable=AsyncMock):
                result = await alert_manager.send_alert(
                    "high_error_rate",
                    {"error_rate": 0.10}
                )
        
        assert result is True
        mock_redis_client.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_alert_channel_failure(self, alert_manager, mock_redis_client):
        """Test alert sending with channel failure."""
        mock_redis_client.get.return_value = None
        
        with patch.object(alert_manager, '_send_email_alert', new_callable=AsyncMock) as mock_email:
            mock_email.side_effect = Exception("Email failed")
            with patch.object(alert_manager, '_send_slack_alert', new_callable=AsyncMock):
                result = await alert_manager.send_alert(
                    "high_error_rate",
                    {"error_rate": 0.10}
                )
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_send_email_alert_no_smtp(self, alert_manager):
        """Test email alert when SMTP not configured."""
        rule = alert_manager.rules["high_error_rate"]
        
        # Should not raise exception
        await alert_manager._send_email_alert(
            rule,
            "Test message",
            {"error_rate": 0.10}
        )
    
    @pytest.mark.asyncio
    async def test_send_slack_alert_no_webhook(self, alert_manager):
        """Test Slack alert when webhook not configured."""
        rule = alert_manager.rules["high_error_rate"]
        
        # Should not raise exception
        await alert_manager._send_slack_alert(
            rule,
            "Test message",
            {"error_rate": 0.10}
        )
    
    @pytest.mark.asyncio
    async def test_send_pagerduty_alert_no_key(self, alert_manager):
        """Test PagerDuty alert when integration key not configured."""
        rule = alert_manager.rules["critical_error"]
        
        # Should not raise exception
        await alert_manager._send_pagerduty_alert(
            rule,
            "Test message",
            {"error_type": "DatabaseError", "error_message": "Connection failed"}
        )
    
    @pytest.mark.asyncio
    async def test_send_slack_alert_with_webhook(self, alert_manager):
        """Test Slack alert with webhook configured."""
        alert_manager.settings.slack_webhook_url = "https://hooks.slack.com/test"
        rule = alert_manager.rules["high_error_rate"]
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_post.return_value.__aenter__.return_value = mock_response
            
            await alert_manager._send_slack_alert(
                rule,
                "Test message",
                {"error_rate": 0.10}
            )
            
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_pagerduty_alert_with_key(self, alert_manager):
        """Test PagerDuty alert with integration key configured."""
        alert_manager.settings.pagerduty_integration_key = "test_key"
        rule = alert_manager.rules["critical_error"]
        
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.status = 202
            mock_post.return_value.__aenter__.return_value = mock_response
            
            await alert_manager._send_pagerduty_alert(
                rule,
                "Test message",
                {"error_type": "DatabaseError"}
            )
            
            mock_post.assert_called_once()
    
    def test_format_context(self, alert_manager):
        """Test context formatting."""
        context = {
            "error_rate": 0.10,
            "threshold": 0.05,
            "service": "api"
        }
        
        result = alert_manager._format_context(context)
        
        assert "error_rate: 0.1" in result
        assert "threshold: 0.05" in result
        assert "service: api" in result
    
    @pytest.mark.asyncio
    async def test_get_alert_status(self, alert_manager, mock_redis_client):
        """Test getting alert status."""
        mock_redis_client.get.return_value = None
        
        status = await alert_manager.get_alert_status()
        
        assert "high_error_rate" in status
        assert "critical_error" in status
        assert status["high_error_rate"]["severity"] == "error"
        assert status["high_error_rate"]["in_cooldown"] is False
    
    @pytest.mark.asyncio
    async def test_get_alert_status_with_cooldown(self, alert_manager, mock_redis_client):
        """Test getting alert status with cooldown active."""
        mock_redis_client.get.return_value = "1"
        
        status = await alert_manager.get_alert_status()
        
        assert all(rule["in_cooldown"] is True for rule in status.values())
    
    @pytest.mark.asyncio
    async def test_message_template_formatting(self, alert_manager):
        """Test message template formatting."""
        context = {"error_rate": 0.10}
        rule = alert_manager.rules["high_error_rate"]
        
        message = rule.message_template.format(**context)
        
        assert "10.00%" in message
        assert "threshold: 5%" in message
    
    @pytest.mark.asyncio
    async def test_critical_alert_all_channels(self, alert_manager, mock_redis_client):
        """Test critical alert uses all channels."""
        mock_redis_client.get.return_value = None
        
        with patch.object(alert_manager, '_send_email_alert', new_callable=AsyncMock) as mock_email:
            with patch.object(alert_manager, '_send_slack_alert', new_callable=AsyncMock) as mock_slack:
                with patch.object(alert_manager, '_send_pagerduty_alert', new_callable=AsyncMock) as mock_pd:
                    await alert_manager.send_alert(
                        "critical_error",
                        {"error_type": "DatabaseError", "error_message": "Connection failed"}
                    )
                    
                    mock_email.assert_called_once()
                    mock_slack.assert_called_once()
                    mock_pd.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_alert_cooldown_prevents_spam(self, alert_manager, mock_redis_client):
        """Test cooldown prevents alert spam."""
        # First alert should succeed
        mock_redis_client.get.return_value = None
        
        with patch.object(alert_manager, '_send_email_alert', new_callable=AsyncMock):
            with patch.object(alert_manager, '_send_slack_alert', new_callable=AsyncMock):
                result1 = await alert_manager.send_alert(
                    "high_error_rate",
                    {"error_rate": 0.10}
                )
        
        assert result1 is True
        
        # Second alert should be blocked by cooldown
        mock_redis_client.get.return_value = "1"
        result2 = await alert_manager.send_alert(
            "high_error_rate",
            {"error_rate": 0.10}
        )
        
        assert result2 is False
