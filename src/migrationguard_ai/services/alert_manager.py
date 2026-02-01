"""
Alert Manager for Critical System Events.

This module implements alerting functionality for critical errors,
anomalies, and system health issues. It supports multiple notification
channels including email, Slack, and PagerDuty.
"""

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
import aiohttp
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from migrationguard_ai.core.config import get_settings
from migrationguard_ai.core.logging import get_logger
from migrationguard_ai.services.redis_client import RedisClient


logger = get_logger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertChannel(str, Enum):
    """Alert notification channels."""
    EMAIL = "email"
    SLACK = "slack"
    PAGERDUTY = "pagerduty"


class AlertRule:
    """
    Alert rule definition.
    
    Attributes:
        name: Rule name
        condition: Condition that triggers the alert
        severity: Alert severity level
        channels: Notification channels to use
        cooldown_minutes: Minimum time between alerts for same rule
        message_template: Template for alert message
    """
    
    def __init__(
        self,
        name: str,
        condition: str,
        severity: AlertSeverity,
        channels: List[AlertChannel],
        cooldown_minutes: int = 15,
        message_template: Optional[str] = None
    ):
        """Initialize alert rule."""
        self.name = name
        self.condition = condition
        self.severity = severity
        self.channels = channels
        self.cooldown_minutes = cooldown_minutes
        self.message_template = message_template or "{message}"


class AlertManager:
    """
    Manages system alerts and notifications.
    
    Handles alert rule evaluation, notification delivery,
    and alert cooldown to prevent notification spam.
    """
    
    def __init__(self, redis_client: RedisClient):
        """
        Initialize alert manager.
        
        Args:
            redis_client: Redis client for cooldown tracking
        """
        self.redis_client = redis_client
        self.settings = get_settings()
        self.rules = self._initialize_rules()
    
    def _initialize_rules(self) -> Dict[str, AlertRule]:
        """
        Initialize default alert rules.
        
        Returns:
            Dictionary of alert rules by name
        """
        return {
            "high_error_rate": AlertRule(
                name="high_error_rate",
                condition="error_rate > 0.05",
                severity=AlertSeverity.ERROR,
                channels=[AlertChannel.EMAIL, AlertChannel.SLACK],
                cooldown_minutes=15,
                message_template="High error rate detected: {error_rate:.2%} (threshold: 5%)"
            ),
            "confidence_drift": AlertRule(
                name="confidence_drift",
                condition="confidence_calibration_error > 0.10",
                severity=AlertSeverity.WARNING,
                channels=[AlertChannel.EMAIL, AlertChannel.SLACK],
                cooldown_minutes=60,
                message_template="Confidence calibration drift detected: {calibration_error:.2%} (threshold: 10%)"
            ),
            "critical_error": AlertRule(
                name="critical_error",
                condition="critical_error_occurred",
                severity=AlertSeverity.CRITICAL,
                channels=[AlertChannel.EMAIL, AlertChannel.SLACK, AlertChannel.PAGERDUTY],
                cooldown_minutes=5,
                message_template="Critical error: {error_type} - {error_message}"
            ),
            "safe_mode_activated": AlertRule(
                name="safe_mode_activated",
                condition="safe_mode_enabled",
                severity=AlertSeverity.CRITICAL,
                channels=[AlertChannel.EMAIL, AlertChannel.SLACK, AlertChannel.PAGERDUTY],
                cooldown_minutes=5,
                message_template="System entered safe mode: {reason}"
            ),
            "service_unavailable": AlertRule(
                name="service_unavailable",
                condition="service_health_check_failed",
                severity=AlertSeverity.ERROR,
                channels=[AlertChannel.EMAIL, AlertChannel.SLACK],
                cooldown_minutes=10,
                message_template="Service unavailable: {service_name} - {error}"
            ),
            "high_latency": AlertRule(
                name="high_latency",
                condition="p95_latency > 120000",
                severity=AlertSeverity.WARNING,
                channels=[AlertChannel.SLACK],
                cooldown_minutes=30,
                message_template="High latency detected: P95={p95_latency}ms (threshold: 120s)"
            ),
            "action_failure_spike": AlertRule(
                name="action_failure_spike",
                condition="action_failure_rate > 0.10",
                severity=AlertSeverity.ERROR,
                channels=[AlertChannel.EMAIL, AlertChannel.SLACK],
                cooldown_minutes=15,
                message_template="Action failure spike: {failure_rate:.2%} (threshold: 10%)"
            ),
        }
    
    async def send_alert(
        self,
        rule_name: str,
        context: Dict[str, Any],
        override_cooldown: bool = False
    ) -> bool:
        """
        Send alert if rule conditions are met and cooldown has expired.
        
        Args:
            rule_name: Name of the alert rule
            context: Context data for alert message
            override_cooldown: Whether to bypass cooldown check
            
        Returns:
            True if alert was sent, False otherwise
        """
        if rule_name not in self.rules:
            logger.warning(f"Unknown alert rule: {rule_name}")
            return False
        
        rule = self.rules[rule_name]
        
        # Check cooldown
        if not override_cooldown:
            if await self._is_in_cooldown(rule_name):
                logger.debug(f"Alert {rule_name} is in cooldown, skipping")
                return False
        
        # Format message
        message = rule.message_template.format(**context)
        
        # Send to all configured channels
        success = True
        for channel in rule.channels:
            try:
                if channel == AlertChannel.EMAIL:
                    await self._send_email_alert(rule, message, context)
                elif channel == AlertChannel.SLACK:
                    await self._send_slack_alert(rule, message, context)
                elif channel == AlertChannel.PAGERDUTY:
                    await self._send_pagerduty_alert(rule, message, context)
            except Exception as e:
                logger.error(f"Failed to send alert via {channel}: {e}")
                success = False
        
        # Set cooldown
        if success:
            await self._set_cooldown(rule_name, rule.cooldown_minutes)
        
        logger.info(
            f"Alert sent: {rule_name}",
            severity=rule.severity.value,
            channels=[c.value for c in rule.channels],
            message=message
        )
        
        return success
    
    async def _is_in_cooldown(self, rule_name: str) -> bool:
        """
        Check if alert rule is in cooldown period.
        
        Args:
            rule_name: Name of the alert rule
            
        Returns:
            True if in cooldown, False otherwise
        """
        key = f"alert:cooldown:{rule_name}"
        value = await self.redis_client.get(key)
        return value is not None
    
    async def _set_cooldown(self, rule_name: str, minutes: int) -> None:
        """
        Set cooldown period for alert rule.
        
        Args:
            rule_name: Name of the alert rule
            minutes: Cooldown duration in minutes
        """
        key = f"alert:cooldown:{rule_name}"
        await self.redis_client.set(key, "1", ex=minutes * 60)
    
    async def _send_email_alert(
        self,
        rule: AlertRule,
        message: str,
        context: Dict[str, Any]
    ) -> None:
        """
        Send alert via email.
        
        Args:
            rule: Alert rule
            message: Alert message
            context: Alert context
        """
        if not self.settings.SMTP_HOST:
            logger.warning("SMTP not configured, skipping email alert")
            return
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = self.settings.SMTP_FROM_EMAIL
        msg['To'] = self.settings.ALERT_EMAIL_RECIPIENTS
        msg['Subject'] = f"[{rule.severity.value.upper()}] MigrationGuard Alert: {rule.name}"
        
        # Build email body
        body = f"""
MigrationGuard AI Alert

Severity: {rule.severity.value.upper()}
Rule: {rule.name}
Time: {datetime.utcnow().isoformat()}

Message:
{message}

Context:
{self._format_context(context)}

---
This is an automated alert from MigrationGuard AI.
"""
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        try:
            with smtplib.SMTP(self.settings.SMTP_HOST, self.settings.SMTP_PORT) as server:
                if self.settings.SMTP_USE_TLS:
                    server.starttls()
                if self.settings.SMTP_USERNAME:
                    server.login(self.settings.SMTP_USERNAME, self.settings.SMTP_PASSWORD)
                server.send_message(msg)
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            raise
    
    async def _send_slack_alert(
        self,
        rule: AlertRule,
        message: str,
        context: Dict[str, Any]
    ) -> None:
        """
        Send alert via Slack webhook.
        
        Args:
            rule: Alert rule
            message: Alert message
            context: Alert context
        """
        if not self.settings.SLACK_WEBHOOK_URL:
            logger.warning("Slack webhook not configured, skipping Slack alert")
            return
        
        # Map severity to Slack color
        color_map = {
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.WARNING: "#ff9900",
            AlertSeverity.ERROR: "#ff0000",
            AlertSeverity.CRITICAL: "#8b0000"
        }
        
        # Build Slack message
        payload = {
            "attachments": [
                {
                    "color": color_map.get(rule.severity, "#808080"),
                    "title": f"MigrationGuard Alert: {rule.name}",
                    "text": message,
                    "fields": [
                        {
                            "title": "Severity",
                            "value": rule.severity.value.upper(),
                            "short": True
                        },
                        {
                            "title": "Time",
                            "value": datetime.utcnow().isoformat(),
                            "short": True
                        }
                    ],
                    "footer": "MigrationGuard AI",
                    "ts": int(datetime.utcnow().timestamp())
                }
            ]
        }
        
        # Add context fields
        for key, value in context.items():
            payload["attachments"][0]["fields"].append({
                "title": key,
                "value": str(value),
                "short": True
            })
        
        # Send to Slack
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.settings.SLACK_WEBHOOK_URL,
                json=payload
            ) as response:
                if response.status != 200:
                    raise Exception(f"Slack API error: {response.status}")
    
    async def _send_pagerduty_alert(
        self,
        rule: AlertRule,
        message: str,
        context: Dict[str, Any]
    ) -> None:
        """
        Send alert via PagerDuty Events API.
        
        Args:
            rule: Alert rule
            message: Alert message
            context: Alert context
        """
        if not self.settings.PAGERDUTY_INTEGRATION_KEY:
            logger.warning("PagerDuty not configured, skipping PagerDuty alert")
            return
        
        # Map severity to PagerDuty severity
        severity_map = {
            AlertSeverity.INFO: "info",
            AlertSeverity.WARNING: "warning",
            AlertSeverity.ERROR: "error",
            AlertSeverity.CRITICAL: "critical"
        }
        
        # Build PagerDuty event
        payload = {
            "routing_key": self.settings.PAGERDUTY_INTEGRATION_KEY,
            "event_action": "trigger",
            "dedup_key": f"migrationguard:{rule.name}",
            "payload": {
                "summary": message,
                "severity": severity_map.get(rule.severity, "error"),
                "source": "MigrationGuard AI",
                "timestamp": datetime.utcnow().isoformat(),
                "custom_details": context
            }
        }
        
        # Send to PagerDuty
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://events.pagerduty.com/v2/enqueue",
                json=payload
            ) as response:
                if response.status != 202:
                    raise Exception(f"PagerDuty API error: {response.status}")
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """
        Format context dictionary for display.
        
        Args:
            context: Context dictionary
            
        Returns:
            Formatted string
        """
        lines = []
        for key, value in context.items():
            lines.append(f"  {key}: {value}")
        return "\n".join(lines)
    
    async def clear_cooldown(self, rule_name: str) -> None:
        """
        Clear cooldown for an alert rule.
        
        Args:
            rule_name: Name of the alert rule
        """
        key = f"alert:cooldown:{rule_name}"
        await self.redis_client.delete(key)
        logger.info(f"Cleared cooldown for alert rule: {rule_name}")
    
    async def get_alert_status(self) -> Dict[str, Any]:
        """
        Get status of all alert rules.
        
        Returns:
            Dictionary with alert rule statuses
        """
        status = {}
        for rule_name, rule in self.rules.items():
            in_cooldown = await self._is_in_cooldown(rule_name)
            status[rule_name] = {
                "severity": rule.severity.value,
                "channels": [c.value for c in rule.channels],
                "cooldown_minutes": rule.cooldown_minutes,
                "in_cooldown": in_cooldown
            }
        return status
