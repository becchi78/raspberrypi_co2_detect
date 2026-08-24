"""Data models for air quality readings and statuses."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AirStatus(str, Enum):
    """Air quality condition status levels based on eCO2 (ppm)."""

    CONDITIONING = "CONDITIONING"
    LOW = "LOW"
    HIGH = "HIGH"
    TOO_HIGH = "TOO HIGH"
    ERROR = "ERROR"

    @property
    def is_alert(self) -> bool:
        """Return True if status indicates high CO2 levels requiring attention."""
        return self in (AirStatus.HIGH, AirStatus.TOO_HIGH)


@dataclass(frozen=True)
class AirQualityData:
    """Represents a single reading from the air quality sensor."""

    eco2_ppm: int
    tvoc_ppb: int
    status: AirStatus
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert data to dictionary for serialization."""
        return {
            "eco2_ppm": self.eco2_ppm,
            "tvoc_ppb": self.tvoc_ppb,
            "status": self.status.value,
            "timestamp": self.timestamp.isoformat(),
        }

    def __str__(self) -> str:
        return f"CO2: {self.eco2_ppm}ppm, TVOC: {self.tvoc_ppb}ppb, Status: {self.status.value}"
