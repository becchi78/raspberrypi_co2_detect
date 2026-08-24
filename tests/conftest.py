"""Pytest fixtures and test doubles for I2C and sensors."""

try:
    import pytest
except ImportError:
    pytest = None

from co2_detector.sensors.ccs811 import EXPECTED_HW_ID, REG_ALG_RESULT_DATA, REG_ERROR_ID, REG_HW_ID, REG_STATUS


class MockSMBus:
    """Mock implementation of smbus2.SMBus for CCS811 testing."""

    def __init__(
        self,
        hw_id: int = EXPECTED_HW_ID,
        status: int = 0x98,  # FW_MODE (0x80) | APP_VALID (0x10) | DATA_READY (0x08)
        eco2: int = 650,
        tvoc: int = 35,
        error_id: int = 0x00,
        raise_on_read: bool = False,
        raise_on_write: bool = False,
    ) -> None:
        self.registers: dict[int, int] = {
            REG_HW_ID: hw_id,
            REG_STATUS: status,
            REG_ERROR_ID: error_id,
        }
        self.eco2 = eco2
        self.tvoc = tvoc
        self.error_id = error_id
        self.raise_on_read = raise_on_read
        self.raise_on_write = raise_on_write
        self.written_bytes: list[tuple[int, int, int]] = []
        self.written_blocks: list[tuple[int, int, list[int]]] = []
        self.is_closed = False

    def read_byte_data(self, i2c_addr: int, register: int) -> int:
        if self.raise_on_read:
            raise OSError("Simulated I2C read failure")
        return self.registers.get(register, 0x00)

    def write_byte_data(self, i2c_addr: int, register: int, value: int) -> None:
        if self.raise_on_write:
            raise OSError("Simulated I2C write failure")
        self.written_bytes.append((i2c_addr, register, value))
        self.registers[register] = value

    def read_i2c_block_data(self, i2c_addr: int, register: int, length: int) -> list[int]:
        if self.raise_on_read:
            raise OSError("Simulated I2C block read failure")
        if register == REG_ALG_RESULT_DATA:
            eco2_msb = (self.eco2 >> 8) & 0xFF
            eco2_lsb = self.eco2 & 0xFF
            tvoc_msb = (self.tvoc >> 8) & 0xFF
            tvoc_lsb = self.tvoc & 0xFF
            status = self.registers.get(REG_STATUS, 0x98)
            error_id = self.registers.get(REG_ERROR_ID, 0x00)
            return [eco2_msb, eco2_lsb, tvoc_msb, tvoc_lsb, status, error_id, 0x00, 0x00][:length]
        return [0] * length

    def write_i2c_block_data(self, i2c_addr: int, register: int, data: list[int]) -> None:
        if self.raise_on_write:
            raise OSError("Simulated I2C block write failure")
        self.written_blocks.append((i2c_addr, register, data))

    def close(self) -> None:
        self.is_closed = True


if pytest is not None:
    @pytest.fixture
    def mock_bus() -> MockSMBus:
        """Fixture providing a standard mock I2C bus."""
        return MockSMBus()
