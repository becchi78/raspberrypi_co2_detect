"""Main air condition monitoring service."""

import json
import logging
import signal
import sys
import time
from typing import Optional

from co2_detector.config import Config
from co2_detector.display.base import BaseDisplay
from co2_detector.display.oled_ssd1306 import DummyDisplay, SSD1306Display
from co2_detector.exceptions import SensorError
from co2_detector.models import AirQualityData, AirStatus
from co2_detector.notifiers.base import BaseNotifier
from co2_detector.notifiers.slack import SlackNotifier
from co2_detector.sensors.base import BaseAirSensor
from co2_detector.sensors.ccs811 import CCS811Sensor

logger = logging.getLogger(__name__)


class AirConditionMonitor:
    """Air condition monitoring coordinator."""

    def __init__(
        self,
        config: Optional[Config] = None,
        sensor: Optional[BaseAirSensor] = None,
        display: Optional[BaseDisplay] = None,
        notifier: Optional[BaseNotifier] = None,
    ) -> None:
        self.config = config or Config()
        self.config.ensure_directories()
        self._setup_logging()

        # Dependencies with DI support
        self.sensor = sensor or CCS811Sensor(
            bus_number=self.config.i2c_bus,
            address=self.config.ccs811_address,
        )

        if display is not None:
            self.display = display
        elif self.config.enable_display:
            self.display = SSD1306Display(
                i2c_address=self.config.ssd1306_address,
                i2c_bus=self.config.i2c_bus,
            )
        else:
            self.display = DummyDisplay()

        if notifier is not None:
            self.notifier = notifier
        else:
            notifiers_list: list[BaseNotifier] = []
            if self.config.enable_slack and self.config.slack_webhook_url:
                notifiers_list.append(
                    SlackNotifier(
                        webhook_url=self.config.slack_webhook_url,
                        channel=self.config.slack_channel,
                        username=self.config.slack_username,
                        icon_emoji=self.config.slack_emoji,
                    )
                )
            if self.config.enable_teams and self.config.teams_webhook_url:
                from co2_detector.notifiers.teams import TeamsNotifier

                notifiers_list.append(
                    TeamsNotifier(
                        webhook_url=self.config.teams_webhook_url,
                    )
                )

            if len(notifiers_list) == 1:
                self.notifier = notifiers_list[0]
            elif len(notifiers_list) > 1:
                from co2_detector.notifiers.base import CompositeNotifier

                self.notifier = CompositeNotifier(notifiers_list)
            else:
                self.notifier = None

        self.current_status: AirStatus = AirStatus.LOW
        self.last_data: Optional[AirQualityData] = None
        self._running = False

    def _setup_logging(self) -> None:
        """Configure file and stream logging based on config."""
        level = getattr(logging, self.config.log_level.upper(), logging.INFO)
        root_logger = logging.getLogger("co2_detector")
        root_logger.setLevel(level)

        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

        # Avoid duplicate handlers if re-initialized
        if not root_logger.handlers:
            # Console handler
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setFormatter(formatter)
            root_logger.addHandler(stream_handler)

            # File handler
            if self.config.log_file:
                file_handler = logging.FileHandler(str(self.config.log_file))
                file_handler.setFormatter(formatter)
                root_logger.addHandler(file_handler)

    def _save_state(self, data: AirQualityData) -> None:
        """Save latest state to JSON state file atomically."""
        if not self.config.state_file:
            return

        temp_file = self.config.state_file.with_suffix(".tmp")
        try:
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data.to_dict(), f, indent=2)
            temp_file.replace(self.config.state_file)
        except Exception as e:
            logger.warning("Failed to save state file: %s", e)

    def step(self) -> Optional[AirQualityData]:
        """Perform a single measurement and notification cycle."""
        if not self.sensor.is_data_ready():
            logger.debug("Sensor data not ready yet.")
            return None

        try:
            eco2, tvoc = self.sensor.read_measurement()
        except SensorError as e:
            logger.error("Error reading from sensor: %s", e)
            if self.notifier:
                self.notifier.notify_error(f"Sensor read error: {e}")
            if self.display:
                self.display.show_message("Sensor Error", str(e)[:20])
            return None

        status = self.config.determine_status(eco2)
        data = AirQualityData(eco2_ppm=eco2, tvoc_ppb=tvoc, status=status)
        self.last_data = data

        if status == AirStatus.CONDITIONING:
            logger.info("Sensor is conditioning/warming up (eCO2: %d ppm)", eco2)
            if self.display:
                self.display.show_message("Conditioning...", f"{eco2} ppm")
            self._save_state(data)
            return data

        # Status change notification
        if status != self.current_status:
            logger.info("Air quality status changed: %s -> %s", self.current_status.value, status.value)
            if self.notifier:
                self.notifier.notify_status_change(data, self.current_status)
            self.current_status = status

        logger.info("Reading: %s", data)

        # Update display
        if self.display:
            self.display.show_air_quality(data)

        # Update persistent state
        self._save_state(data)

        return data

    def stop(self) -> None:
        """Stop the monitoring loop gracefully."""
        self._running = False
        logger.info("Stopping AirConditionMonitor...")

    def run(self) -> None:
        """Start continuous monitoring loop."""
        self._running = True

        def _signal_handler(signum: int, frame: object) -> None:
            logger.info("Received signal %d, initiating shutdown...", signum)
            self.stop()

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

        logger.info("Starting AirConditionMonitor loop (interval: %.1fs)...", self.config.interval_seconds)

        if self.display:
            self.display.show_message("CO2 Monitor", "Starting...")

        # Wait until sensor produces first data or interrupted
        while self._running and not self.sensor.is_data_ready():
            time.sleep(1)

        while self._running:
            try:
                data = self.step()
                if data and data.status == AirStatus.CONDITIONING:
                    # Longer wait during sensor burn-in / conditioning
                    sleep_time = min(self.config.warmup_wait_seconds, 60.0)
                else:
                    sleep_time = self.config.interval_seconds

                # Sleep in small slices to respond to stop signal quickly
                end_time = time.time() + sleep_time
                while self._running and time.time() < end_time:
                    time.sleep(min(1.0, max(0.1, end_time - time.time())))

            except Exception as e:
                logger.exception("Unexpected error in monitoring cycle: %s", e)
                if self.notifier:
                    self.notifier.notify_error(f"Unexpected monitor error: {e}")
                time.sleep(10)

        # Cleanup
        logger.info("Cleaning up resources...")
        if self.display:
            self.display.clear()
            self.display.close()
        if self.sensor:
            self.sensor.close()
        logger.info("Monitor shutdown complete.")
