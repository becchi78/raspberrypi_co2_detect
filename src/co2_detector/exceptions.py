"""Custom exception hierarchy for CO2 detector."""


class CO2DetectorError(Exception):
    """Base exception for all co2_detector errors."""


class SensorError(CO2DetectorError):
    """Base exception for sensor-related errors."""


class SensorInitError(SensorError):
    """Raised when sensor initialization fails."""


class DeviceNotFoundError(SensorInitError):
    """Raised when sensor hardware ID does not match expected ID."""


class SensorFirmwareError(SensorInitError):
    """Raised when sensor firmware mode or bootloader fails."""


class SensorReadError(SensorError):
    """Raised when reading sensor data fails."""


class DisplayError(CO2DetectorError):
    """Base exception for display-related errors."""


class NotifierError(CO2DetectorError):
    """Base exception for notification errors."""
