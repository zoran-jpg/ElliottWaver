from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _read(path: str) -> str:
    return (_repo_root() / path).read_text(encoding="utf-8")


def test_project_documents_define_clear_responsibilities() -> None:
    manifest = _read("PROJECT_MANIFEST.md")

    assert "Documentation Responsibilities" in manifest
    assert "CURRENT_STATUS.md" in manifest
    assert "ROADMAP.md" in manifest
    assert "METRICS.md" in manifest
    assert "DECISIONS.md" in manifest
    assert "ELLIOTTWAVER_MASTER_CONTROL.md" in manifest


def test_current_status_and_metrics_keep_open_actions_gate_explicit() -> None:
    current_status = _read("docs/project/status/CURRENT_STATUS.md")
    metrics = _read("docs/project/METRICS.md")

    assert "GitHub Actions" in current_status
    assert "pending" in current_status.lower()
    assert "matrix" in current_status.lower()
    assert "pending" in metrics.lower()


def test_decisions_reference_existing_adrs() -> None:
    decisions = _read("docs/project/DECISIONS.md")
    adr_dir = _repo_root() / "docs" / "adr"

    expected_adrs = (
        "0001-clean-architecture.md",
        "0002-desktop-controller-view-separation.md",
        "0003-desktop-thread-queue-after-model.md",
        "0004-chart-contract-and-rendering-boundary.md",
        "0005-dependency-ci-packaging-strategy.md",
    )

    for adr in expected_adrs:
        assert (adr_dir / adr).exists()
        assert f"docs/adr/{adr}" in decisions
