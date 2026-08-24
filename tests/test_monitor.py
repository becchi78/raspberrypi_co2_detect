"""Tests for AirConditionMonitor service."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from co2_detector.config import Config
from co2_detector.display.oled_ssd1306 import DummyDisplay
from co2_detector.exceptions import SensorReadError
from co2_detector.models import AirQualityData, AirStatus
from co2_detector.monitor import AirConditionMonitor
from co2_detector.sensors.base import BaseAirSensor


class DummySensor(BaseAirSensor):
    """Dummy sensor implementation for test isolation."""

    def __init__(self, eco2: int = 700, tvoc: int = 25, ready: bool = True) -> None:
        self.eco2 = eco2
        self.tvoc = tvoc
        self.ready = ready
        self.raise_error = False

    def is_data_ready(self) -> bool:
        return self.ready

    def read_measurement(self) -> tuple[int, int]:
        if self.raise_error:
            raise SensorReadError("Simulated sensor failure")
        return self.eco2, self.tvoc

    def close(self) -> None:
        pass


class TestMonitor(unittest.TestCase):
    def test_monitor_init_and_step_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            state_file = tmp_path / "latest_state.json"
            log_file = tmp_path / "monitor.log"
            config = Config(log_dir=tmp_path, log_file=log_file, state_file=state_file)

            sensor = DummySensor(eco2=800, tvoc=30)
            display = DummyDisplay()
            notifier = MagicMock()

            monitor = AirConditionMonitor(
                config=config,
                sensor=sensor,
                display=display,
                notifier=notifier,
            )

            data = monitor.step()
            self.assertIsNotNone(data)
            assert data is not None
            self.assertEqual(data.eco2_ppm, 800)
            self.assertEqual(data.tvoc_ppb, 30)
            self.assertEqual(data.status, AirStatus.LOW)
            self.assertEqual(display.last_data, data)

            # Verify JSON state file output
            self.assertTrue(state_file.exists())
            with open(state_file, encoding="utf-8") as f:
                saved = json.load(f)
            self.assertEqual(saved["eco2_ppm"], 800)
            self.assertEqual(saved["status"], "LOW")

    def test_monitor_step_not_ready(self) -> None:
        sensor = DummySensor(ready=False)
        display = DummyDisplay()
        monitor = AirConditionMonitor(config=Config(), sensor=sensor, display=display)

        data = monitor.step()
        self.assertIsNone(data)
        self.assertIsNone(display.last_data)

    def test_monitor_step_status_change_triggers_notification(self) -> None:
        sensor = DummySensor(eco2=1500, tvoc=100)
        display = DummyDisplay()
        notifier = MagicMock()

        monitor = AirConditionMonitor(
            config=Config(),
            sensor=sensor,
            display=display,
            notifier=notifier,
        )
        monitor.current_status = AirStatus.LOW

        data = monitor.step()
        self.assertIsNotNone(data)
        assert data is not None
        self.assertEqual(data.status, AirStatus.HIGH)
        self.assertTrue(notifier.notify_status_change.called)
        self.assertEqual(monitor.current_status, AirStatus.HIGH)

    def test_monitor_step_sensor_error_handling(self) -> None:
        sensor = DummySensor()
        sensor.raise_error = True
        display = DummyDisplay()
        notifier = MagicMock()

        monitor = AirConditionMonitor(
            config=Config(),
            sensor=sensor,
            display=display,
            notifier=notifier,
        )

        data = monitor.step()
        self.assertIsNone(data)
        self.assertTrue(notifier.notify_error.called)
        self.assertIsNotNone(display.last_message)
        assert display.last_message is not None
        self.assertIn("Sensor Error", display.last_message[0])

    def test_monitor_stop(self) -> None:
        monitor = AirConditionMonitor(
            config=Config(),
            sensor=DummySensor(),
            display=DummyDisplay(),
        )
        monitor._running = True
        monitor.stop()
        self.assertFalse(monitor._running)


if __name__ == "__main__":
    unittest.main()
