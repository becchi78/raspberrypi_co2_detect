"""OLED display implementation for SSD1306 128x64."""

import logging
from pathlib import Path
from typing import Any

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None  # type: ignore[assignment]
    ImageDraw = None  # type: ignore[assignment]
    ImageFont = None  # type: ignore[assignment]

from co2_detector.display.base import BaseDisplay
from co2_detector.exceptions import DisplayError
from co2_detector.models import AirQualityData

logger = logging.getLogger(__name__)

# Common Japanese font paths on Debian / Raspberry Pi OS
DEFAULT_FONT_CANDIDATES = [
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "fonts-japanese-gothic.ttf",
]


class SSD1306Display(BaseDisplay):
    """SSD1306 OLED (128x64) display controller using Pillow."""

    def __init__(
        self,
        width: int = 128,
        height: int = 64,
        i2c_address: int = 0x3C,
        i2c_bus: int = 1,
        font_path: str | None = None,
        driver: Any | None = None,
    ) -> None:
        self.width = width
        self.height = height
        self.i2c_address = i2c_address
        self.i2c_bus = i2c_bus
        self.font_path = font_path

        self._font_title = self._load_font(size=18)
        self._font_value = self._load_font(size=24)
        self._font_sub = self._load_font(size=12)

        self._driver = driver
        if self._driver is None:
            self._driver = self._init_hardware_driver()

        self.last_image: Any | None = None

    def _init_hardware_driver(self) -> Any | None:
        """Try to initialize hardware SSD1306 driver, gracefully handle missing hardware/libs."""
        # 1. Try modern adafruit-circuitpython-ssd1306
        try:
            import board  # type: ignore[import-not-found]
            import busio  # type: ignore[import-not-found]
            from adafruit_ssd1306 import SSD1306_I2C  # type: ignore[import-not-found]

            i2c = busio.I2C(board.SCL, board.SDA)
            disp = SSD1306_I2C(self.width, self.height, i2c, addr=self.i2c_address)
            disp.fill(0)
            disp.show()
            logger.info("Initialized modern SSD1306_I2C hardware driver.")
            return disp
        except Exception as e1:
            logger.debug("Modern adafruit_ssd1306 not available: %s", e1)

        # 2. Try legacy Adafruit_SSD1306
        try:
            import Adafruit_SSD1306  # type: ignore[import-not-found]

            disp = Adafruit_SSD1306.SSD1306_128_64(rst=None, i2c_address=self.i2c_address)
            disp.begin()
            disp.clear()
            disp.display()
            logger.info("Initialized legacy Adafruit_SSD1306 driver.")
            return disp
        except Exception as e2:
            logger.debug("Legacy Adafruit_SSD1306 not available: %s", e2)

        logger.warning(
            "No hardware OLED driver available. Operating in virtual/headless display mode."
        )
        return None

    def _load_font(self, size: int) -> Any:
        """Find and load available TTF font, or fallback to default bitmap font."""
        if ImageFont is None:
            return None

        candidates = []
        if self.font_path:
            candidates.append(self.font_path)
        candidates.extend(DEFAULT_FONT_CANDIDATES)

        for path_str in candidates:
            path = Path(path_str)
            if path.is_file():
                try:
                    return ImageFont.truetype(str(path), size)
                except Exception:
                    continue

        return ImageFont.load_default()

    def render_air_quality_image(self, data: AirQualityData) -> Any:
        """Create a 1-bit monochrome PIL Image depicting current air quality."""
        if Image is None or ImageDraw is None:
            raise DisplayError(
                "Pillow is required for SSD1306 image rendering. Please install pillow."
            )

        image = Image.new("1", (self.width, self.height), 0)
        draw = ImageDraw.Draw(image)

        # Title / Label
        draw.text((0, 0), "CO2 Level", font=self._font_title, fill=255)

        # CO2 value
        co2_str = f"{data.eco2_ppm:,} ppm"
        draw.text((0, 20), co2_str, font=self._font_value, fill=255)

        # Sub info: TVOC & Status
        sub_str = f"TVOC:{data.tvoc_ppb}ppb [{data.status.value}]"
        draw.text((0, 48), sub_str, font=self._font_sub, fill=255)

        return image

    def render_message_image(self, line1: str, line2: str = "") -> Any:
        """Create a 1-bit monochrome PIL Image depicting a message."""
        if Image is None or ImageDraw is None:
            raise DisplayError(
                "Pillow is required for SSD1306 image rendering. Please install pillow."
            )

        image = Image.new("1", (self.width, self.height), 0)
        draw = ImageDraw.Draw(image)

        draw.text((0, 4), line1, font=self._font_title, fill=255)
        if line2:
            draw.text((0, 32), line2, font=self._font_sub, fill=255)

        return image

    def _display_image(self, image: Any) -> None:
        """Send image to hardware display if driver is present."""
        self.last_image = image

        if self._driver is None or image is None:
            return

        try:
            # Modern adafruit_ssd1306 API
            if hasattr(self._driver, "image") and hasattr(self._driver, "show"):
                self._driver.image(image)
                self._driver.show()
            # Legacy Adafruit_SSD1306 API
            elif hasattr(self._driver, "image") and hasattr(self._driver, "display"):
                self._driver.image(image)
                self._driver.display()
        except Exception as e:
            raise DisplayError(f"Failed to send image to OLED: {e}") from e

    def show_air_quality(self, data: AirQualityData) -> None:
        """Render and display air quality data."""
        if Image is not None:
            img = self.render_air_quality_image(data)
            self._display_image(img)

    def show_message(self, line1: str, line2: str = "") -> None:
        """Render and display message text."""
        if Image is not None:
            img = self.render_message_image(line1, line2)
            self._display_image(img)

    def clear(self) -> None:
        """Clear display."""
        if Image is not None:
            blank = Image.new("1", (self.width, self.height), 0)
            self._display_image(blank)

    def close(self) -> None:
        """Clean up display."""
        self.clear()


class DummyDisplay(BaseDisplay):
    """No-op display for testing or headless environments."""

    def __init__(self) -> None:
        self.last_data: AirQualityData | None = None
        self.last_message: tuple[str, str] | None = None
        self.cleared = False

    def show_air_quality(self, data: AirQualityData) -> None:
        self.last_data = data
        self.cleared = False

    def show_message(self, line1: str, line2: str = "") -> None:
        self.last_message = (line1, line2)
        self.cleared = False

    def clear(self) -> None:
        self.cleared = True

    def close(self) -> None:
        self.clear()
