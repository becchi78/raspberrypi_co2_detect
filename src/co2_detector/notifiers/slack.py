"""Slack Incoming Webhook Notifier."""

import json
import logging
import urllib.error
import urllib.request
from typing import Any, Optional

from co2_detector.exceptions import NotifierError
from co2_detector.models import AirQualityData, AirStatus
from co2_detector.notifiers.base import BaseNotifier

logger = logging.getLogger(__name__)


class SlackNotifier(BaseNotifier):
    """Sends notifications to Slack via Incoming Webhooks using standard library."""

    def __init__(
        self,
        webhook_url: str,
        channel: str = "#air_condition_monitor",
        username: str = "AIR_CONDITION_MONITOR",
        icon_emoji: str = ":loudspeaker:",
        timeout: float = 10.0,
    ) -> None:
        self.webhook_url = webhook_url
        self.channel = channel
        self.username = username
        self.icon_emoji = icon_emoji
        self.timeout = timeout

    def _post(self, payload: dict[str, Any]) -> bool:
        if not self.webhook_url:
            logger.debug("Slack webhook URL not set; skipping notification.")
            return False

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status = resp.status
                if status == 200:
                    logger.info("Successfully sent Slack notification.")
                    return True
                logger.warning("Slack notification returned status %d", status)
                return False
        except urllib.error.URLError as e:
            logger.error("Failed to send Slack notification: %s", e)
            return False
        except Exception as e:
            logger.error("Unexpected error sending Slack notification: %s", e)
            raise NotifierError(f"Slack notification error: {e}") from e

    def notify_status_change(self, data: AirQualityData, old_status: AirStatus) -> bool:
        """Send notification to Slack when status changes."""
        color = "good"
        if data.status == AirStatus.HIGH:
            color = "warning"
        elif data.status in (AirStatus.TOO_HIGH, AirStatus.ERROR):
            color = "danger"

        fallback = f"CO2 level is {data.status.value}: {data.eco2_ppm:,} ppm (TVOC: {data.tvoc_ppb} ppb)"
        payload = {
            "channel": self.channel,
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "attachments": [
                {
                    "fallback": fallback,
                    "color": color,
                    "title": f"Air Quality Status Changed: {data.status.value}",
                    "text": fallback,
                    "fields": [
                        {"title": "eCO2", "value": f"{data.eco2_ppm:,} ppm", "short": True},
                        {"title": "TVOC", "value": f"{data.tvoc_ppb} ppb", "short": True},
                        {"title": "Previous Status", "value": old_status.value, "short": True},
                    ],
                }
            ],
        }
        return self._post(payload)

    def notify_error(self, message: str) -> bool:
        """Send error alert to Slack."""
        payload = {
            "channel": self.channel,
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "attachments": [
                {
                    "fallback": f"Error: {message}",
                    "color": "danger",
                    "title": "Air Condition Monitor Error",
                    "text": message,
                }
            ],
        }
        return self._post(payload)
