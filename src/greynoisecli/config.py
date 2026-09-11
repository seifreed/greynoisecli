import os
import tomllib
from pathlib import Path


class ConfigError(ValueError):
    pass


def default_config_path() -> Path:
    configured = os.getenv("GREYNOISE_CONFIG")
    if configured:
        return Path(configured).expanduser()
    root = (
        os.getenv("APPDATA") or os.getenv("XDG_CONFIG_HOME") or Path.home() / ".config"
    )
    return Path(root) / "greynoise" / "config.toml"


def load_api_key(config_path: Path | None = None) -> str | None:
    environment_key = os.getenv("GREYNOISE")
    if environment_key and environment_key.strip():
        return environment_key.strip()

    path = config_path or default_config_path()
    if not path.is_file():
        return None
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
        section = document.get("greynoise", {})
        api_key = section.get("api_key") if isinstance(section, dict) else None
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(f"Cannot read GreyNoise config {path}: {error}") from error
    if not isinstance(api_key, str) or not api_key.strip():
        raise ConfigError(f"GreyNoise config {path} must contain greynoise.api_key")
    return api_key.strip()
