"""Command line interface for CO2 detector."""

import argparse
import json
import sys
import time
from collections.abc import Sequence

from co2_detector.config import Config
from co2_detector.display.oled_ssd1306 import SSD1306Display
from co2_detector.models import AirQualityData
from co2_detector.monitor import AirConditionMonitor
from co2_detector.sensors.ccs811 import CCS811Sensor


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="co2-detector",
        description="Raspberry Pi Air Quality (CO2 & TVOC) Monitor",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Command: run (Default continuous monitor)
    run_parser = subparsers.add_parser(
        "run", help="Start continuous air quality monitoring service"
    )
    run_parser.add_argument(
        "--interval",
        type=float,
        default=60.0,
        help="Sampling interval in seconds (default: 60)",
    )
    run_parser.add_argument(
        "--no-display", action="store_true", help="Disable OLED display updates"
    )
    run_parser.add_argument("--slack", action="store_true", help="Enable Slack alerts")
    run_parser.add_argument("--webhook-url", type=str, default=None, help="Slack webhook URL")
    run_parser.add_argument("--teams", action="store_true", help="Enable Microsoft Teams alerts")
    run_parser.add_argument(
        "--teams-webhook-url",
        type=str,
        default=None,
        help="Microsoft Teams webhook URL",
    )
    run_parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level",
    )

    # Command: read (Single reading)
    read_parser = subparsers.add_parser("read", help="Perform a single air quality measurement")
    read_parser.add_argument("--json", action="store_true", help="Output measurement as JSON")

    # Command: display (Update display with latest state)
    disp_parser = subparsers.add_parser("display", help="Render latest reading onto OLED display")
    disp_parser.add_argument(
        "--co2", type=int, default=None, help="Directly specify CO2 ppm to display"
    )
    disp_parser.add_argument(
        "--tvoc", type=int, default=0, help="Directly specify TVOC ppb to display"
    )

    return parser


def handle_run(args: argparse.Namespace, config: Config) -> int:
    """Execute continuous monitoring."""
    config.interval_seconds = args.interval
    config.enable_display = not args.no_display
    config.log_level = args.log_level
    if args.slack:
        config.enable_slack = True
    if args.webhook_url:
        config.slack_webhook_url = args.webhook_url
        config.enable_slack = True
    if args.teams:
        config.enable_teams = True
    if args.teams_webhook_url:
        config.teams_webhook_url = args.teams_webhook_url
        config.enable_teams = True

    monitor = AirConditionMonitor(config=config)
    try:
        monitor.run()
    except KeyboardInterrupt:
        pass
    return 0


def handle_read(args: argparse.Namespace, config: Config) -> int:
    """Execute single measurement."""
    try:
        sensor = CCS811Sensor(bus_number=config.i2c_bus, address=config.ccs811_address)
    except Exception as e:
        sys.stderr.write(f"Error initializing sensor: {e}\n")
        return 1

    try:
        # Wait up to 5 seconds for data
        for _ in range(50):
            if sensor.is_data_ready():
                break
            time.sleep(0.1)

        eco2, tvoc = sensor.read_measurement()
        status = config.determine_status(eco2)
        data = AirQualityData(eco2_ppm=eco2, tvoc_ppb=tvoc, status=status)

        if args.json:
            print(json.dumps(data.to_dict(), indent=2))
        else:
            print(f"CO2: {eco2} ppm | TVOC: {tvoc} ppb | Status: {status.value}")
        return 0
    except Exception as e:
        sys.stderr.write(f"Error reading sensor: {e}\n")
        return 1
    finally:
        sensor.close()


def handle_display(args: argparse.Namespace, config: Config) -> int:
    """Update OLED display."""
    display = SSD1306Display(i2c_address=config.ssd1306_address, i2c_bus=config.i2c_bus)
    try:
        if args.co2 is not None:
            status = config.determine_status(args.co2)
            data = AirQualityData(eco2_ppm=args.co2, tvoc_ppb=args.tvoc, status=status)
        elif config.state_file and config.state_file.exists():
            with open(config.state_file, encoding="utf-8") as f:
                raw = json.load(f)
            data = AirQualityData(
                eco2_ppm=raw["eco2_ppm"],
                tvoc_ppb=raw["tvoc_ppb"],
                status=config.determine_status(raw["eco2_ppm"]),
            )
        else:
            sys.stderr.write("No state data available and --co2 not provided.\n")
            return 1

        display.show_air_quality(data)
        return 0
    finally:
        display.close()


def main(argv: Sequence[str] | None = None) -> int:
    """Main CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.command:
        # Default to 'run' if no subcommand provided
        args = parser.parse_args(["run"] + (sys.argv[1:] if argv is None else list(argv)))

    config = Config.from_env()

    if args.command == "run":
        return handle_run(args, config)
    elif args.command == "read":
        return handle_read(args, config)
    elif args.command == "display":
        return handle_display(args, config)
    return 0


if __name__ == "__main__":
    sys.exit(main())
