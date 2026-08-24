"""Sensor modules."""

from co2_detector.sensors.base import BaseAirSensor
from co2_detector.sensors.ccs811 import CCS811Sensor

__all__ = ["BaseAirSensor", "CCS811Sensor"]
