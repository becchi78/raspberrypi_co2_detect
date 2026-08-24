"""Tests for configuration management."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from co2_detector.config import Config
from co2_detector.models import AirStatus


class TestConfig(unittest.TestCase):
    def test_default_config(self) -> None:
        config = Config()
        self.assertEqual(config.i2c_bus, 1)
        self.assertEqual(config.ccs811_address, 0x5B)
        self.assertEqual(config.ssd1306_address, 0x3C)
        self.assertEqual(config.co2_threshold_1, 1000)
        self.assertEqual(config.co2_threshold_2, 2000)
        self.assertEqual(config.interval_seconds, 60.0)
        self.assertTrue(config.enable_display)
        self.assertFalse(config.enable_slack)
        self.assertFalse(config.enable_teams)

    def test_config_from_env(self) -> None:
        env_vars = {
            "CO2_I2C_BUS": "2",
            "CO2_CCS811_ADDRESS": "0x5A",
            "CO2_SSD1306_ADDRESS": "0x3D",
            "CO2_THRESHOLD_1": "1200",
            "CO2_THRESHOLD_2": "2500",
            "CO2_INTERVAL_SECONDS": "30",
            "CO2_ENABLE_DISPLAY": "false",
            "CO2_ENABLE_SLACK": "true",
            "CO2_SLACK_WEBHOOK_URL": "https://hooks.slack.com/test",
            "CO2_ENABLE_TEAMS": "true",
            "CO2_TEAMS_WEBHOOK_URL": "https://outlook.office.com/webhook/test",
            "CO2_LOG_LEVEL": "DEBUG",
        }
        with mock.patch.dict(os.environ, env_vars):
            config = Config.from_env()
            self.assertEqual(config.i2c_bus, 2)
            self.assertEqual(config.ccs811_address, 0x5A)
            self.assertEqual(config.ssd1306_address, 0x3D)
            self.assertEqual(config.co2_threshold_1, 1200)
            self.assertEqual(config.co2_threshold_2, 2500)
            self.assertEqual(config.interval_seconds, 30.0)
            self.assertFalse(config.enable_display)
            self.assertTrue(config.enable_slack)
            self.assertEqual(config.slack_webhook_url, "https://hooks.slack.com/test")
            self.assertTrue(config.enable_teams)
            self.assertEqual(config.teams_webhook_url, "https://outlook.office.com/webhook/test")
            self.assertEqual(config.log_level, "DEBUG")

    def test_determine_status(self) -> None:
        config = Config(co2_threshold_1=1000, co2_threshold_2=2000)

        # Conditioning out of bounds
        self.assertEqual(config.determine_status(350), AirStatus.CONDITIONING)
        self.assertEqual(config.determine_status(9000), AirStatus.CONDITIONING)

        # Normal levels
        self.assertEqual(config.determine_status(400), AirStatus.LOW)
        self.assertEqual(config.determine_status(800), AirStatus.LOW)
        self.assertEqual(config.determine_status(999), AirStatus.LOW)

        # High levels
        self.assertEqual(config.determine_status(1000), AirStatus.HIGH)
        self.assertEqual(config.determine_status(1500), AirStatus.HIGH)
        self.assertEqual(config.determine_status(1999), AirStatus.HIGH)

        # Too High levels
        self.assertEqual(config.determine_status(2000), AirStatus.TOO_HIGH)
        self.assertEqual(config.determine_status(3000), AirStatus.TOO_HIGH)

    def test_ensure_directories(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            log_dir = Path(tmp_dir) / "sub" / "logs"
            config = Config(log_dir=log_dir)
            self.assertFalse(log_dir.exists())
            config.ensure_directories()
            self.assertTrue(log_dir.exists())


if __name__ == "__main__":
    unittest.main()
