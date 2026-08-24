"""Tests for OLED display modules."""

import unittest
from unittest.mock import MagicMock

try:
    from PIL import Image
except ImportError:  # pragma: no cover
    Image = None

from co2_detector.display.oled_ssd1306 import DummyDisplay, SSD1306Display
from co2_detector.exceptions import DisplayError
from co2_detector.models import AirQualityData, AirStatus


class TestDisplay(unittest.TestCase):
    def test_dummy_display(self) -> None:
        disp = DummyDisplay()
        data = AirQualityData(eco2_ppm=800, tvoc_ppb=20, status=AirStatus.LOW)

        disp.show_air_quality(data)
        self.assertEqual(disp.last_data, data)
        self.assertFalse(disp.cleared)

        disp.show_message("Test", "Message")
        self.assertEqual(disp.last_message, ("Test", "Message"))

        disp.clear()
        self.assertTrue(disp.cleared)

        disp.close()
        self.assertTrue(disp.cleared)

    @unittest.skipIf(Image is None, "Pillow is not installed in local runtime")
    def test_ssd1306_render_images(self) -> None:
        disp = SSD1306Display(width=128, height=64, driver=None)
        data = AirQualityData(eco2_ppm=1200, tvoc_ppb=80, status=AirStatus.HIGH)

        img_air = disp.render_air_quality_image(data)
        assert Image is not None
        self.assertIsInstance(img_air, Image.Image)
        self.assertEqual(img_air.size, (128, 64))
        self.assertEqual(img_air.mode, "1")

        img_msg = disp.render_message_image("Header", "Detail")
        self.assertIsInstance(img_msg, Image.Image)
        self.assertEqual(img_msg.size, (128, 64))
        self.assertEqual(img_msg.mode, "1")

    @unittest.skipIf(Image is None, "Pillow is not installed in local runtime")
    def test_ssd1306_with_mock_driver(self) -> None:
        mock_hw = MagicMock()
        disp = SSD1306Display(width=128, height=64, driver=mock_hw)
        data = AirQualityData(eco2_ppm=600, tvoc_ppb=10, status=AirStatus.LOW)

        disp.show_air_quality(data)
        self.assertTrue(mock_hw.image.called)
        self.assertTrue(mock_hw.show.called or mock_hw.display.called)

        disp.clear()
        self.assertIsNotNone(disp.last_image)

    @unittest.skipIf(Image is None, "Pillow is not installed in local runtime")
    def test_ssd1306_driver_error(self) -> None:
        mock_hw = MagicMock()
        mock_hw.image.side_effect = Exception("Hardware communication error")
        disp = SSD1306Display(width=128, height=64, driver=mock_hw)
        data = AirQualityData(eco2_ppm=600, tvoc_ppb=10, status=AirStatus.LOW)

        with self.assertRaises(DisplayError):
            disp.show_air_quality(data)


if __name__ == "__main__":
    unittest.main()
