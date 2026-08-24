"""Microsoft Teams Incoming Webhook Notifier."""

import json
import logging
import urllib.error
import urllib.request
from typing import Any

from co2_detector.exceptions import NotifierError
from co2_detector.models import AirQualityData, AirStatus
from co2_detector.notifiers.base import BaseNotifier

logger = logging.getLogger(__name__)


class TeamsNotifier(BaseNotifier):
    """Sends notifications to Microsoft Teams via Incoming Webhooks / Workflows using standard library."""

    def __init__(
        self,
        webhook_url: str,
        timeout: float = 10.0,
    ) -> None:
        self.webhook_url = webhook_url
        self.timeout = timeout

    def _post(self, payload: dict[str, Any]) -> bool:
        if not self.webhook_url:
            logger.debug("Teams webhook URL not set; skipping notification.")
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
                if status in (200, 202):
                    logger.info("Successfully sent Teams notification.")
                    return True
                logger.warning("Teams notification returned status %d", status)
                return False
        except urllib.error.URLError as e:
            logger.error("Failed to send Teams notification: %s", e)
            return False
        except Exception as e:
            logger.error("Unexpected error sending Teams notification: %s", e)
            raise NotifierError(f"Teams notification error: {e}") from e

    def notify_status_change(self, data: AirQualityData, old_status: AirStatus) -> bool:
        """Send notification to Teams when air quality status changes."""
        # MessageCard theme colors (Hex without #)
        theme_color = "2EB886"  # Green / Good
        if data.status == AirStatus.HIGH:
            theme_color = "DAA038"  # Warning / Yellow
        elif data.status in (AirStatus.TOO_HIGH, AirStatus.ERROR):
            theme_color = "A30200"  # Danger / Red

        title = f"Air Quality Status Changed: {data.status.value}"
        summary = f"CO2 level is {data.status.value}: {data.eco2_ppm:,} ppm"

        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": theme_color,
            "summary": summary,
            "sections": [
                {
                    "activityTitle": f"📢 **{title}**",
                    "activitySubtitle": summary,
                    "facts": [
                        {"name": "eCO2", "value": f"{data.eco2_ppm:,} ppm"},
                        {"name": "TVOC", "value": f"{data.tvoc_ppb} ppb"},
                        {"name": "Previous Status", "value": old_status.value},
                    ],
                    "markdown": True,
                }
            ],
        }
        return self._post(payload)

    def notify_error(self, message: str) -> bool:
        """Send error alert to Teams."""
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "A30200",
            "summary": f"Air Condition Monitor Error: {message}",
            "sections": [
                {
                    "activityTitle": "🚨 **Air Condition Monitor Error**",
                    "activitySubtitle": message,
                    "markdown": True,
                }
            ],
        }
        return self._post(payload)
