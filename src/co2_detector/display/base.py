"""Base display interface."""

from abc import ABC, abstractmethod

from co2_detector.models import AirQualityData


class BaseDisplay(ABC):
    """Abstract interface for status displays."""

    @abstractmethod
    def show_air_quality(self, data: AirQualityData) -> None:
        """Render air quality information on the display."""
        ...

    @abstractmethod
    def show_message(self, line1: str, line2: str = "") -> None:
        """Render general message text on the display."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Clear the display buffer and screen."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Clean up display resources."""
        ...
