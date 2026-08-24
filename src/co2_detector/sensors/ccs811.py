"""CCS811 Air Quality (eCO2 & TVOC) Sensor Driver."""

import logging
import time
from enum import IntEnum
from typing import Self

from co2_detector.exceptions import (
    DeviceNotFoundError,
    SensorFirmwareError,
    SensorInitError,
    SensorReadError,
)
from co2_detector.sensors.base import BaseAirSensor, I2CBusProtocol

logger = logging.getLogger(__name__)


class DriveMode(IntEnum):
    """Measurement drive modes for CCS811."""

    IDLE = 0x00
    EVERY_1SEC = 0x01
    EVERY_10SEC = 0x02
    EVERY_60SEC = 0x03
    EVERY_250MS = 0x04


# CCS811 I2C Registers
REG_STATUS = 0x00
REG_MEAS_MODE = 0x01
REG_ALG_RESULT_DATA = 0x02
REG_RAW_DATA = 0x03
REG_ENV_DATA = 0x05
REG_THRESHOLDS = 0x10
REG_BASELINE = 0x11
REG_HW_ID = 0x20
REG_HW_VERSION = 0x21
REG_FW_BOOT_VERSION = 0x23
REG_FW_APP_VERSION = 0x24
REG_ERROR_ID = 0xE0
REG_APP_START = 0xF4
REG_SW_RESET = 0xFF

# Hardware ID constant
EXPECTED_HW_ID = 0x81

# Status Register Bitmasks
STATUS_ERROR_BIT = 0x01
STATUS_DATA_READY_BIT = 0x08
STATUS_APP_VALID_BIT = 0x10
STATUS_FW_MODE_BIT = 0x80


class CCS811Sensor(BaseAirSensor):
    """Driver for the AMS CCS811 digital gas sensor."""

    DEFAULT_ADDRESS = 0x5B

    def __init__(
        self,
        bus_number: int = 1,
        address: int = DEFAULT_ADDRESS,
        mode: DriveMode = DriveMode.EVERY_1SEC,
        bus: I2CBusProtocol | None = None,
    ) -> None:
        self.address = address
        self._owned_bus = False

        if bus is not None:
            self._bus = bus
        else:
            try:
                import smbus2  # type: ignore[import-not-found,import-untyped]

                self._bus = smbus2.SMBus(bus_number)
                self._owned_bus = True
            except Exception as e:
                raise SensorInitError(f"Failed to open I2C bus {bus_number}: {e}") from e

        self.mode = mode
        self._eco2 = 0
        self._tvoc = 0

        self._initialize()

    def _initialize(self) -> None:
        """Initialize the sensor, verify hardware ID, and switch to app mode."""
        hw_id = self._read_u8(REG_HW_ID)
        if hw_id != EXPECTED_HW_ID:
            raise DeviceNotFoundError(
                f"CCS811 hardware ID mismatch! Expected 0x{EXPECTED_HW_ID:02X}, got 0x{hw_id:02X}."
            )

        # Transition sensor from boot mode to application mode
        self._write_list(REG_APP_START, [])
        time.sleep(0.1)

        status = self._read_status()
        if status & STATUS_ERROR_BIT:
            error_code = self._read_u8(REG_ERROR_ID)
            raise SensorFirmwareError(
                f"CCS811 reported error after APP_START (Error ID: 0x{error_code:02X})."
            )

        if not (status & STATUS_FW_MODE_BIT):
            raise SensorFirmwareError(
                "CCS811 failed to enter firmware application mode (FW_MODE bit not set)."
            )

        # Set drive mode
        self.set_drive_mode(self.mode)
        logger.info("CCS811 sensor initialized successfully at address 0x%02X", self.address)

    def _read_status(self) -> int:
        return self._read_u8(REG_STATUS)

    def set_drive_mode(self, mode: DriveMode) -> None:
        """Set sensor measurement drive mode (idle, 1s, 10s, 60s, 250ms)."""
        meas_mode = (mode.value << 4) & 0x70
        self._write_u8(REG_MEAS_MODE, meas_mode)
        self.mode = mode
        logger.debug("Set CCS811 drive mode to %s (0x%02X)", mode.name, meas_mode)

    def is_data_ready(self) -> bool:
        """Return True if new measurement data is ready."""
        status = self._read_status()
        return bool(status & STATUS_DATA_READY_BIT)

    def read_measurement(self) -> tuple[int, int]:
        """Read eCO2 (ppm) and TVOC (ppb) from sensor.

        Returns:
            tuple[int, int]: (eCO2 in ppm, TVOC in ppb)

        Raises:
            SensorReadError: If sensor reports an internal error or read fails.
        """
        status = self._read_status()
        if status & STATUS_ERROR_BIT:
            error_id = self._read_u8(REG_ERROR_ID)
            raise SensorReadError(f"CCS811 status error flag set (Error ID: 0x{error_id:02X})")

        buf = self._read_list(REG_ALG_RESULT_DATA, 8)
        self._eco2 = (buf[0] << 8) | buf[1]
        self._tvoc = (buf[2] << 8) | buf[3]

        logger.debug("Read CCS811: eCO2=%d ppm, TVOC=%d ppb", self._eco2, self._tvoc)
        return self._eco2, self._tvoc

    @property
    def eco2(self) -> int:
        """Latest eCO2 reading in ppm."""
        return self._eco2

    @property
    def tvoc(self) -> int:
        """Latest TVOC reading in ppb."""
        return self._tvoc

    def _read_u8(self, register: int) -> int:
        try:
            return self._bus.read_byte_data(self.address, register) & 0xFF
        except Exception as e:
            raise SensorReadError(
                f"Failed to read byte from reg 0x{register:02X} at 0x{self.address:02X}: {e}"
            ) from e

    def _write_u8(self, register: int, value: int) -> None:
        try:
            self._bus.write_byte_data(self.address, register, value & 0xFF)
        except Exception as e:
            raise SensorReadError(
                f"Failed to write byte 0x{value:02X} to reg 0x{register:02X}: {e}"
            ) from e

    def _read_list(self, register: int, length: int) -> list[int]:
        try:
            return self._bus.read_i2c_block_data(self.address, register, length)
        except Exception as e:
            raise SensorReadError(
                f"Failed to read {length} bytes from reg 0x{register:02X}: {e}"
            ) from e

    def _write_list(self, register: int, data: list[int]) -> None:
        try:
            self._bus.write_i2c_block_data(self.address, register, data)
        except Exception as e:
            raise SensorReadError(f"Failed to write data to reg 0x{register:02X}: {e}") from e

    def close(self) -> None:
        """Close I2C bus connection if owned."""
        if self._owned_bus and hasattr(self._bus, "close"):
            try:
                self._bus.close()
            except Exception as e:
                logger.warning("Error closing I2C bus: %s", e)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.close()
