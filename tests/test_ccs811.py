"""Tests for CCS811 sensor driver with Mock SMBus."""

import unittest

from co2_detector.exceptions import (
    DeviceNotFoundError,
    SensorFirmwareError,
    SensorReadError,
)
from co2_detector.sensors.ccs811 import (
    REG_ERROR_ID,
    REG_MEAS_MODE,
    REG_STATUS,
    CCS811Sensor,
    DriveMode,
)
from tests.conftest import MockSMBus


class TestCCS811(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_bus = MockSMBus()

    def test_ccs811_successful_init(self) -> None:
        sensor = CCS811Sensor(bus=self.mock_bus)
        self.assertEqual(sensor.address, 0x5B)
        self.assertEqual(sensor.mode, DriveMode.EVERY_1SEC)
        self.assertIn((0x5B, REG_MEAS_MODE, 0x10), self.mock_bus.written_bytes)

    def test_ccs811_hw_id_mismatch(self) -> None:
        bus = MockSMBus(hw_id=0x99)  # Wrong ID
        with self.assertRaises(DeviceNotFoundError):
            CCS811Sensor(bus=bus)

    def test_ccs811_firmware_status_error(self) -> None:
        bus = MockSMBus(status=0x81, error_id=0x04)  # ERROR bit set (0x01)
        with self.assertRaises(SensorFirmwareError):
            CCS811Sensor(bus=bus)

    def test_ccs811_fw_mode_not_set(self) -> None:
        bus = MockSMBus(status=0x18)  # FW_MODE bit (0x80) not set
        with self.assertRaises(SensorFirmwareError):
            CCS811Sensor(bus=bus)

    def test_ccs811_is_data_ready(self) -> None:
        sensor = CCS811Sensor(bus=self.mock_bus)

        # DATA_READY bit is 0x08
        self.mock_bus.registers[REG_STATUS] = 0x98  # Ready
        self.assertTrue(sensor.is_data_ready())

        self.mock_bus.registers[REG_STATUS] = 0x90  # Not ready
        self.assertFalse(sensor.is_data_ready())

    def test_ccs811_read_measurement(self) -> None:
        self.mock_bus.eco2 = 780
        self.mock_bus.tvoc = 55
        sensor = CCS811Sensor(bus=self.mock_bus)

        eco2, tvoc = sensor.read_measurement()
        self.assertEqual(eco2, 780)
        self.assertEqual(tvoc, 55)
        self.assertEqual(sensor.eco2, 780)
        self.assertEqual(sensor.tvoc, 55)

    def test_ccs811_read_measurement_error_flag(self) -> None:
        sensor = CCS811Sensor(bus=self.mock_bus)
        self.mock_bus.registers[REG_STATUS] = 0x99  # Error bit set
        self.mock_bus.registers[REG_ERROR_ID] = 0x02

        with self.assertRaises(SensorReadError):
            sensor.read_measurement()

    def test_ccs811_read_i2c_bus_failure(self) -> None:
        sensor = CCS811Sensor(bus=self.mock_bus)
        self.mock_bus.raise_on_read = True

        with self.assertRaises(SensorReadError):
            sensor.read_measurement()

    def test_ccs811_set_drive_mode(self) -> None:
        sensor = CCS811Sensor(bus=self.mock_bus)
        sensor.set_drive_mode(DriveMode.EVERY_10SEC)
        self.assertEqual(sensor.mode, DriveMode.EVERY_10SEC)
        self.assertIn((0x5B, REG_MEAS_MODE, 0x20), self.mock_bus.written_bytes)

    def test_ccs811_context_manager(self) -> None:
        self.mock_bus.is_closed = False
        with CCS811Sensor(bus=self.mock_bus) as sensor:
            self.assertEqual(sensor.address, 0x5B)


if __name__ == "__main__":
    unittest.main()
