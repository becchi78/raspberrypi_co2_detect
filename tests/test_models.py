"""Tests for data models and AirStatus enum."""

import unittest
from datetime import UTC, datetime

from co2_detector.models import AirQualityData, AirStatus


class TestModels(unittest.TestCase):
    def test_air_status_enum(self) -> None:
        self.assertEqual(AirStatus.LOW.value, "LOW")
        self.assertEqual(AirStatus.HIGH.value, "HIGH")
        self.assertEqual(AirStatus.TOO_HIGH.value, "TOO HIGH")
        self.assertEqual(AirStatus.CONDITIONING.value, "CONDITIONING")

        self.assertFalse(AirStatus.LOW.is_alert)
        self.assertFalse(AirStatus.CONDITIONING.is_alert)
        self.assertTrue(AirStatus.HIGH.is_alert)
        self.assertTrue(AirStatus.TOO_HIGH.is_alert)

    def test_air_quality_data_creation_and_serialization(self) -> None:
        now = datetime(2026, 8, 24, 12, 0, 0, tzinfo=UTC)
        data = AirQualityData(
            eco2_ppm=850,
            tvoc_ppb=42,
            status=AirStatus.LOW,
            timestamp=now,
        )

        self.assertEqual(data.eco2_ppm, 850)
        self.assertEqual(data.tvoc_ppb, 42)
        self.assertEqual(data.status, AirStatus.LOW)
        self.assertEqual(data.timestamp, now)

        d = data.to_dict()
        self.assertEqual(d["eco2_ppm"], 850)
        self.assertEqual(d["tvoc_ppb"], 42)
        self.assertEqual(d["status"], "LOW")
        self.assertEqual(d["timestamp"], "2026-08-24T12:00:00+00:00")

        self.assertIn("850ppm", str(data))
        self.assertIn("42ppb", str(data))


if __name__ == "__main__":
    unittest.main()
