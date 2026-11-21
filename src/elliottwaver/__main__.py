"""Executable module entrypoint for ElliottWaver desktop MVP."""

import argparse
import sys
from collections.abc import Sequence

from elliottwaver.interfaces import launch_analysis_desktop


def _build_argument_parser() -> argparse.ArgumentParser:
    return argparse.ArgumentParser(
        prog="elliottwaver",
        description="ElliottWaver desktop analysis application.",
    )


def main(argv: Sequence[str] | None = ()) -> None:
    """Start the desktop MVP application."""

    parsed_argv = list(argv) if argv is not None else None
    _build_argument_parser().parse_args(parsed_argv)
    launch_analysis_desktop()


if __name__ == "__main__":
    main(sys.argv[1:])
