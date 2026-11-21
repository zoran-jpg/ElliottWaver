"""Smoke checks for installed wheel distribution."""

from __future__ import annotations

import importlib
import subprocess
import sys

MODULES = [
    "elliottwaver",
    "elliottwaver.application.chart_contract",
    "elliottwaver.infrastructure.analysis.swing_preparation_adapter",
    "elliottwaver.interfaces.chart_tk",
]


def _verify_imports() -> None:
    for module_name in MODULES:
        importlib.import_module(module_name)


def _verify_cli_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "elliottwaver", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        message = f"CLI smoke check failed with exit code {result.returncode}: {result.stderr}"
        raise RuntimeError(message)


def main() -> int:
    _verify_imports()
    _verify_cli_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
