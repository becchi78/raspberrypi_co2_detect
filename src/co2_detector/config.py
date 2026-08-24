"""Configuration management for CO2 detector."""

import os
from dataclasses import dataclass, field
from pathlib import Path

from co2_detector.models import AirStatus


@dataclass
class Config:
    """Application configuration with sensible defaults and environment variable overrides."""

    # I2C Settings
    i2c_bus: int = 1
    ccs811_address: int = 0x5B
    ssd1306_address: int = 0x3C

    # CO2 Thresholds (ppm)
    co2_threshold_1: int = 1000
    co2_threshold_2: int = 2000
    co2_lower_limit: int = 400
    co2_higher_limit: int = 8192

    # Intervals (seconds)
    interval_seconds: float = 60.0
    warmup_wait_seconds: float = 1200.0

    # Paths
    base_dir: Path = field(default_factory=lambda: Path(__file__).resolve().parent.parent.parent)
    log_dir: Path | None = None
    log_file: Path | None = None
    state_file: Path | None = None

    # Feature Toggles
    enable_display: bool = True
    enable_slack: bool = False
    enable_teams: bool = False

    # Slack Settings
    slack_webhook_url: str = ""
    slack_username: str = "AIR_CONDITION_MONITOR"
    slack_channel: str = "#air_condition_monitor"
    slack_emoji: str = ":loudspeaker:"

    # Microsoft Teams Settings
    teams_webhook_url: str = ""

    # Logging
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        if self.log_dir is None:
            self.log_dir = self.base_dir / "logs"
        if self.log_file is None:
            self.log_file = self.log_dir / "air_condition_monitor.log"
        if self.state_file is None:
            self.state_file = self.log_dir / "latest_state.json"

    def ensure_directories(self) -> None:
        """Create log and runtime directories if they do not exist."""
        if self.log_dir:
            self.log_dir.mkdir(parents=True, exist_ok=True)

    def determine_status(self, eco2_ppm: int) -> AirStatus:
        """Determine AirStatus category based on CO2 ppm level."""
        if eco2_ppm < self.co2_lower_limit or eco2_ppm > self.co2_higher_limit:
            return AirStatus.CONDITIONING
        if eco2_ppm < self.co2_threshold_1:
            return AirStatus.LOW
        if eco2_ppm < self.co2_threshold_2:
            return AirStatus.HIGH
        return AirStatus.TOO_HIGH

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration overriding defaults with environment variables."""
        return cls(
            i2c_bus=int(os.getenv("CO2_I2C_BUS", "1")),
            ccs811_address=int(os.getenv("CO2_CCS811_ADDRESS", "0x5B"), 16),
            ssd1306_address=int(os.getenv("CO2_SSD1306_ADDRESS", "0x3C"), 16),
            co2_threshold_1=int(os.getenv("CO2_THRESHOLD_1", "1000")),
            co2_threshold_2=int(os.getenv("CO2_THRESHOLD_2", "2000")),
            interval_seconds=float(os.getenv("CO2_INTERVAL_SECONDS", "60.0")),
            enable_display=os.getenv("CO2_ENABLE_DISPLAY", "true").lower() in ("true", "1", "yes"),
            enable_slack=os.getenv("CO2_ENABLE_SLACK", "false").lower() in ("true", "1", "yes"),
            slack_webhook_url=os.getenv("CO2_SLACK_WEBHOOK_URL", ""),
            slack_channel=os.getenv("CO2_SLACK_CHANNEL", "#air_condition_monitor"),
            enable_teams=os.getenv("CO2_ENABLE_TEAMS", "false").lower() in ("true", "1", "yes"),
            teams_webhook_url=os.getenv("CO2_TEAMS_WEBHOOK_URL", ""),
            log_level=os.getenv("CO2_LOG_LEVEL", "INFO"),
        )
