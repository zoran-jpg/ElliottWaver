from elliottwaver.core.config.settings import (
    Environment,
    Settings,
    get_settings,
)


def test_default_settings() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_name == "ElliottWaver"
    assert settings.environment == Environment.DEVELOPMENT
    assert settings.debug is False
    assert settings.timezone == "UTC"


def test_cached_settings() -> None:
    get_settings.cache_clear()

    first = get_settings()
    second = get_settings()

    assert first is second
