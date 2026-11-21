from __future__ import annotations

import tomllib
from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_pyproject_exposes_console_script_for_desktop_entrypoint() -> None:
    pyproject = _repo_root() / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))

    scripts = data["project"]["scripts"]
    assert scripts["elliottwaver"] == "elliottwaver.__main__:main"


def test_makefile_install_uses_interpreter_bound_pip() -> None:
    makefile = (_repo_root() / "Makefile").read_text(encoding="utf-8")

    assert 'python -m pip install -c constraints/dev.txt -e ".[dev]"' in makefile
    assert '\npip install -e ".[dev]"' not in makefile


def test_constraints_files_pin_runtime_and_dev_dependencies() -> None:
    runtime = (_repo_root() / "constraints" / "runtime.txt").read_text(encoding="utf-8")
    dev = (_repo_root() / "constraints" / "dev.txt").read_text(encoding="utf-8")

    assert "pydantic==" in runtime
    assert "pydantic-core==" in runtime
    assert "pydantic-settings==" in runtime
    assert "structlog==" in runtime
    assert "typing-extensions==" in runtime
    assert "-c runtime.txt" in dev
    assert "build==" in dev
    assert "ruff==" in dev
    assert "pytest==" in dev


def test_pyproject_uses_ruff_as_single_formatter_standard() -> None:
    pyproject = _repo_root() / "pyproject.toml"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))

    assert "ruff" in " ".join(data["project"]["optional-dependencies"]["dev"])
    assert "tool" in data
    assert "ruff" in data["tool"]
    assert "black" not in " ".join(data["project"]["optional-dependencies"]["dev"])
    assert "black" not in data.get("tool", {})


def test_quality_workflow_uses_cross_platform_matrix_and_constraints() -> None:
    workflow = (_repo_root() / ".github" / "workflows" / "quality.yml").read_text(encoding="utf-8")

    assert "os: [ubuntu-latest, windows-latest]" in workflow
    assert 'python -m pip install -c constraints/dev.txt -e ".[dev]"' in workflow
    assert "xvfb-run -a python -m pytest" in workflow


def test_quality_workflow_contains_wheel_smoke_job() -> None:
    workflow = (_repo_root() / ".github" / "workflows" / "quality.yml").read_text(encoding="utf-8")

    assert "wheel-smoke:" in workflow
    assert "python -m build --wheel" in workflow
    assert "python -m pip check" in workflow
    assert "engineering/scripts/wheel_smoke.py" in workflow


def test_wheel_smoke_script_validates_imports_and_cli() -> None:
    script = (_repo_root() / "engineering" / "scripts" / "wheel_smoke.py").read_text(
        encoding="utf-8"
    )

    assert '"elliottwaver.interfaces.chart_tk"' in script
    assert '"elliottwaver.infrastructure.analysis.swing_preparation_adapter"' in script
    assert '[sys.executable, "-m", "elliottwaver", "--help"]' in script
