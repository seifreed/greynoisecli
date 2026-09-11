from pathlib import Path

import pytest

from greynoisecli.config import ConfigError, default_config_path, load_api_key
from tests.support import environment, expect


def test_config_sources_and_errors(tmp_path: Path) -> None:
    explicit = tmp_path / "explicit.toml"
    xdg = tmp_path / "xdg"
    appdata = tmp_path / "appdata"
    with environment(GREYNOISE_CONFIG=str(explicit)):
        expect(default_config_path() == explicit)
    with environment(
        GREYNOISE_CONFIG=None, APPDATA=str(appdata), XDG_CONFIG_HOME=str(xdg)
    ):
        expect(default_config_path() == appdata / "greynoise" / "config.toml")
    with environment(GREYNOISE_CONFIG=None, APPDATA=None, XDG_CONFIG_HOME=str(xdg)):
        expect(default_config_path() == xdg / "greynoise" / "config.toml")
    with environment(GREYNOISE_CONFIG=None, APPDATA=None, XDG_CONFIG_HOME=None):
        expect(
            default_config_path()
            == Path.home() / ".config" / "greynoise" / "config.toml"
        )

    config = tmp_path / "config.toml"
    config.write_text('[greynoise]\napi_key = "from-file"\n', encoding="utf-8")
    with environment(GREYNOISE="  from-env  "):
        expect(load_api_key(config) == "from-env")
    with environment(GREYNOISE=""):
        expect(load_api_key(config) == "from-file")
        expect(load_api_key(tmp_path / "absent.toml") is None)

    with environment(GREYNOISE=None):
        config.write_text('greynoise = "wrong"\n', encoding="utf-8")
        with pytest.raises(ConfigError, match="must contain"):
            load_api_key(config)
        config.write_text("not valid toml =", encoding="utf-8")
        with pytest.raises(ConfigError, match="Cannot read"):
            load_api_key(config)
        config.write_bytes(b"\xff")
        with pytest.raises(ConfigError, match="Cannot read"):
            load_api_key(config)
