"""Configuration management for BMCForge."""

import tomllib
from pathlib import Path
from typing import Any

import tomli_w

APP_DIR = Path.home() / ".bmcforge"
CONFIG_PATH = APP_DIR / "config.toml"

DEFAULT_CONFIG = {
    "general": {
        "default_platform": "youtube",
        "editor": "",
    },
    "paths": {
        "broll_dir": "",
        "sfx_dir": "",
        "music_dir": "",
        "exports_dir": "",
    },
    "api": {
        "openrouter_key": "",
        "llm_model": "tngtech/deepseek-r1t2-chimera:free",
    },
    "youtube": {
        "credentials_path": "~/.bmcforge/youtube_client_secrets.json",
        "default_privacy": "private",
        "default_category": "people_blogs",
        "notify_subscribers": True,
    },
    "instagram": {
        "access_token": "",
        "user_id": "",
    },
    "display": {
        "date_format": "%Y-%m-%d",
        "show_file_sizes": True,
        "color_theme": "auto",
    },
    "defaults": {
        "content_type": "video",
        "shot_duration": 5,
    },
}


def ensure_app_dir() -> Path:
    """Ensure the application directory exists."""
    APP_DIR.mkdir(parents=True, exist_ok=True)
    return APP_DIR


def load_config() -> dict[str, Any]:
    """Load configuration from TOML file."""
    ensure_app_dir()

    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def save_config(config: dict[str, Any]) -> None:
    """Save configuration to TOML file."""
    ensure_app_dir()

    with open(CONFIG_PATH, "wb") as f:
        tomli_w.dump(config, f)


def get_config_value(key: str) -> Any:
    """Get a configuration value by dot-separated key.

    Example: get_config_value("api.openrouter_key")
    """
    config = load_config()
    parts = key.split(".")

    value = config
    for part in parts:
        if isinstance(value, dict) and part in value:
            value = value[part]
        else:
            return None

    return value


def set_config_value(key: str, value: Any) -> None:
    """Set a configuration value by dot-separated key.

    Example: set_config_value("api.openrouter_key", "sk-...")
    """
    config = load_config()
    parts = key.split(".")

    # Navigate to the parent dict
    current = config
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]

    # Set the value
    current[parts[-1]] = value
    save_config(config)
