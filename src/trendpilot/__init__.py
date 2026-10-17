"""TrendPilot's local company research agent and UI entry point."""

from trendpilot.agent import run

__all__ = ["run", "main"]


def main() -> None:
    import sys

    from trendpilot.cli import main as cli_main

    sys.exit(cli_main())
