"""Tests for TeamsNotifier and CompositeNotifier."""

import json
import unittest
from unittest.mock import MagicMock, patch

from co2_detector.models import AirQualityData, AirStatus
from co2_detector.notifiers.base import CompositeNotifier
from co2_detector.notifiers.teams import TeamsNotifier


class TestTeams(unittest.TestCase):
    def test_teams_notifier_no_url(self) -> None:
        notifier = TeamsNotifier(webhook_url="")
        data = AirQualityData(eco2_ppm=850, tvoc_ppb=25, status=AirStatus.LOW)
        self.assertFalse(notifier.notify_status_change(data, AirStatus.CONDITIONING))
        self.assertFalse(notifier.notify_error("test error"))

    def test_teams_notifier_status_change_success(self) -> None:
        notifier = TeamsNotifier(webhook_url="https://outlook.office.com/webhook/test")
        data = AirQualityData(eco2_ppm=1800, tvoc_ppb=150, status=AirStatus.HIGH)

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            result = notifier.notify_status_change(data, AirStatus.LOW)
            self.assertTrue(result)

            req = mock_urlopen.call_args[0][0]
            payload = json.loads(req.data.decode("utf-8"))
            self.assertEqual(payload["@type"], "MessageCard")
            self.assertEqual(payload["themeColor"], "DAA038")  # Warning color
            self.assertIn("1,800 ppm", payload["summary"])

    def test_teams_notifier_error_notification(self) -> None:
        notifier = TeamsNotifier(webhook_url="https://outlook.office.com/webhook/test")

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__.return_value = mock_resp

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_urlopen:
            result = notifier.notify_error("Sensor connection failed")
            self.assertTrue(result)

            req = mock_urlopen.call_args[0][0]
            payload = json.loads(req.data.decode("utf-8"))
            self.assertEqual(payload["themeColor"], "A30200")
            self.assertIn("Sensor connection failed", payload["sections"][0]["activitySubtitle"])

    def test_composite_notifier(self) -> None:
        mock_n1 = MagicMock()
        mock_n1.notify_status_change.return_value = True
        mock_n1.notify_error.return_value = True

        mock_n2 = MagicMock()
        mock_n2.notify_status_change.return_value = False
        mock_n2.notify_error.return_value = False

        comp = CompositeNotifier([mock_n1, mock_n2])
        data = AirQualityData(eco2_ppm=700, tvoc_ppb=15, status=AirStatus.LOW)

        self.assertTrue(comp.notify_status_change(data, AirStatus.CONDITIONING))
        self.assertTrue(mock_n1.notify_status_change.called)
        self.assertTrue(mock_n2.notify_status_change.called)

        self.assertTrue(comp.notify_error("alert"))
        self.assertTrue(mock_n1.notify_error.called)
        self.assertTrue(mock_n2.notify_error.called)


if __name__ == "__main__":
    unittest.main()
