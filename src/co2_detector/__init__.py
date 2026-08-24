"""CO2 and Air Quality Monitor package."""

from co2_detector.config import Config
from co2_detector.models import AirQualityData, AirStatus

__version__ = "1.0.0"
__all__ = ["Config", "AirQualityData", "AirStatus"]
