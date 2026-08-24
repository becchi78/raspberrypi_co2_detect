"""Tests for SlackNotifier."""

import json
import unittest
import urllib.error
from unittest.mock import MagicMock, patch

from co2_detector.models import AirQualityData, AirStatus
from co2_detector.notifiers.slack import SlackNotifier


class TestSlack(unittest.TestCase):
    def test_slack_notifier_no_url(self) -> None:
        notifier = SlackNotifier(webhook_url="")
        data = AirQualityData(eco2_ppm=900, tvoc_ppb=30, status=AirStatus.LOW)
        self.assertFalse(notifier.notify_status_change(data, AirStatus.CONDITIONING))
        self.assertFalse(notifier.notify_error("some error"))

    def test_slack_notifier_status_change_success(self) -> None:
        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/test/xxx/yyy")
        data = AirQualityData(eco2_ppm=1600, tvoc_ppb=120, status=AirStatus.HIGH)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            result = notifier.notify_status_change(data, AirStatus.LOW)
            self.assertTrue(result)
            self.assertTrue(mock_urlopen.called)

            # Verify request payload
            req = mock_urlopen.call_args[0][0]
            payload = json.loads(req.data.decode("utf-8"))
            self.assertEqual(payload["channel"], "#air_condition_monitor")
            self.assertEqual(payload["attachments"][0]["color"], "warning")
            self.assertIn("1,600 ppm", payload["attachments"][0]["fallback"])

    def test_slack_notifier_error_notification(self) -> None:
        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/test/xxx/yyy")

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            result = notifier.notify_error("Critical sensor fault")
            self.assertTrue(result)

            req = mock_urlopen.call_args[0][0]
            payload = json.loads(req.data.decode("utf-8"))
            self.assertEqual(payload["attachments"][0]["color"], "danger")
            self.assertIn("Critical sensor fault", payload["attachments"][0]["text"])

    def test_slack_notifier_http_error(self) -> None:
        notifier = SlackNotifier(webhook_url="https://hooks.slack.com/services/test/xxx/yyy")
        data = AirQualityData(eco2_ppm=1600, tvoc_ppb=120, status=AirStatus.HIGH)

        with patch(
            "urllib.request.urlopen", side_effect=urllib.error.URLError("Network unreachable")
        ):
            result = notifier.notify_status_change(data, AirStatus.LOW)
            self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
