"""Base notifier interface."""

from abc import ABC, abstractmethod
from typing import Optional

from co2_detector.models import AirQualityData, AirStatus


class BaseNotifier(ABC):
    """Abstract interface for alert notifiers."""

    @abstractmethod
    def notify_status_change(self, data: AirQualityData, old_status: AirStatus) -> bool:
        """Send notification when air quality status changes."""
        ...

    @abstractmethod
    def notify_error(self, message: str) -> bool:
        """Send notification on monitor or sensor failure."""
        ...


class CompositeNotifier(BaseNotifier):
    """Dispatches notifications to multiple underlying notifiers."""

    def __init__(self, notifiers: Optional[list[BaseNotifier]] = None) -> None:
        self.notifiers: list[BaseNotifier] = [n for n in (notifiers or []) if n is not None]

    def add(self, notifier: Optional[BaseNotifier]) -> None:
        """Add a notifier to the composite."""
        if notifier is not None:
            self.notifiers.append(notifier)

    def notify_status_change(self, data: AirQualityData, old_status: AirStatus) -> bool:
        results = [n.notify_status_change(data, old_status) for n in self.notifiers]
        return any(results) if results else False

    def notify_error(self, message: str) -> bool:
        results = [n.notify_error(message) for n in self.notifiers]
        return any(results) if results else False

