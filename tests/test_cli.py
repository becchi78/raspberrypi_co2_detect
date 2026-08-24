"""Tests for command line interface."""

import io
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from co2_detector.cli import build_parser, main
from co2_detector.models import AirQualityData, AirStatus
from tests.conftest import MockSMBus


class TestCLI(unittest.TestCase):
    def test_cli_parser_defaults(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["run"])
        self.assertEqual(args.command, "run")
        self.assertEqual(args.interval, 60.0)
        self.assertFalse(args.no_display)

    def test_cli_parser_options(self) -> None:
        parser = build_parser()
        args = parser.parse_args([
            "run",
            "--interval",
            "15",
            "--no-display",
            "--slack",
            "--teams",
            "--teams-webhook-url",
            "https://test.teams",
            "--log-level",
            "DEBUG",
        ])
        self.assertEqual(args.command, "run")
        self.assertEqual(args.interval, 15.0)
        self.assertTrue(args.no_display)
        self.assertTrue(args.slack)
        self.assertTrue(args.teams)
        self.assertEqual(args.teams_webhook_url, "https://test.teams")
        self.assertEqual(args.log_level, "DEBUG")

    def test_cli_read_json_output(self) -> None:
        mock_sensor = MagicMock()
        mock_sensor.is_data_ready.return_value = True
        mock_sensor.read_measurement.return_value = (850, 45)
        with patch("co2_detector.cli.CCS811Sensor", return_value=mock_sensor):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                exit_code = main(["read", "--json"])
                self.assertEqual(exit_code, 0)
                captured = mock_stdout.getvalue()
                data = json.loads(captured)
                self.assertEqual(data["eco2_ppm"], 850)
                self.assertEqual(data["tvoc_ppb"], 45)
                self.assertEqual(data["status"], "LOW")

    def test_cli_display_direct(self) -> None:
        with patch("co2_detector.cli.SSD1306Display") as mock_disp_cls:
            mock_disp = MagicMock()
            mock_disp_cls.return_value = mock_disp

            exit_code = main(["display", "--co2", "1500", "--tvoc", "90"])
            self.assertEqual(exit_code, 0)
            self.assertTrue(mock_disp.show_air_quality.called)
            data: AirQualityData = mock_disp.show_air_quality.call_args[0][0]
            self.assertEqual(data.eco2_ppm, 1500)
            self.assertEqual(data.status, AirStatus.HIGH)


if __name__ == "__main__":
    unittest.main()
