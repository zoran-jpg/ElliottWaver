import pytest

from elliottwaver import __main__


def test_main_starts_desktop_launcher(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def fake_launch() -> None:
        calls.append("called")

    monkeypatch.setattr(__main__, "launch_analysis_desktop", fake_launch)

    __main__.main()

    assert calls == ["called"]
