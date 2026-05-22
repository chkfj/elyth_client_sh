import json
import os
from pathlib import Path

DEFAULT_SETTINGS = {
    "auto_refresh_enabled": True,
    "auto_refresh_interval": 30
}

def get_settings_path() -> Path:
    """設定ファイルのパスを取得 (プロジェクトルートに保存)"""
    return Path(__file__).parent.parent / "settings.json"

def load_settings() -> dict:
    """設定ファイルを読み込む"""
    settings_path = get_settings_path()
    if settings_path.exists():
        try:
            with open(settings_path, "r") as f:
                settings = json.load(f)
                merged = DEFAULT_SETTINGS.copy()
                merged.update(settings)
                return merged
        except (json.JSONDecodeError, IOError):
            return DEFAULT_SETTINGS.copy()
    return DEFAULT_SETTINGS.copy()

def save_settings(settings: dict) -> None:
    """設定ファイルを保存"""
    settings_path = get_settings_path()
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    with open(settings_path, "w") as f:
        json.dump(settings, f, indent=2)