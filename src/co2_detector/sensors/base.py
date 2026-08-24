"""Base sensor abstract interface."""

from abc import ABC, abstractmethod
from typing import Protocol, runtime_checkable


@runtime_checkable
class I2CBusProtocol(Protocol):
    """Protocol for SMBus/I2C communication to enable mocking and DI."""

    def read_byte_data(self, i2c_addr: int, register: int) -> int: ...

    def write_byte_data(self, i2c_addr: int, register: int, value: int) -> None: ...

    def read_i2c_block_data(self, i2c_addr: int, register: int, length: int) -> list[int]: ...

    def write_i2c_block_data(self, i2c_addr: int, register: int, data: list[int]) -> None: ...

    def close(self) -> None: ...


class BaseAirSensor(ABC):
    """Abstract base class for air quality sensors."""

    @abstractmethod
    def is_data_ready(self) -> bool:
        """Check if new measurement data is available."""
        ...

    @abstractmethod
    def read_measurement(self) -> tuple[int, int]:
        """Read latest measurement.

        Returns:
            tuple[int, int]: (eCO2 in ppm, TVOC in ppb)
        """
        ...

    @abstractmethod
    def close(self) -> None:
        """Release underlying bus/sensor resources."""
        ...
