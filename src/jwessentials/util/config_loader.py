from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from endstone import Logger


_DEFAULT_CONFIG = {
    "general": {
        "default-home-limit": 3,
        "spawn-on-join": False,
        "spawn-world": "",
        "teleport-delay": 0,
        "teleport-safety-enabled": True,
        "world-teleport-permissions": True,
    },
    "economy": {
        "use-jweconomy": True,
        "starting-balance": 1000.0,
    },
    "chat": {
        "format": "{prefix}{displayname}: {message}",
        "max-length": 256,
        "message-cooldown": 0,
    },
    "commands": {
        "msg-aliases": ["message", "whisper", "tell", "dm"],
        "reply-aliases": ["r"],
        "socialspy-aliases": ["ss"],
    },
    "performance": {
        "cache-ttl": 300,
        "cache-max-size": 500,
    },
    "rtp": {
        "max-x": 10000,
        "max-z": 10000,
        "min-y": 64,
        "max-y": 320,
        "cooldown-seconds": 30,
        "center-x": 0,
        "center-z": 0,
        "max-attempts": 10,
    },
    "jail": {
        "x": 0,
        "y": 100,
        "z": 0,
        "world": "main",
    },
    "debug": False,
}


class ConfigLoader:

    def __init__(self, data_folder: Path, logger: Logger) -> None:
        self._data_folder = data_folder
        self._logger = logger
        self._config: dict[str, Any] = {}
        self._scoreboard_defaults: dict[str, Any] = {}
        self._bossbar_defaults: dict[str, Any] = {}

    @property
    def general_config(self) -> dict[str, Any]:
        return self._config.get("general", _DEFAULT_CONFIG["general"])

    @property
    def economy_config(self) -> dict[str, Any]:
        return self._config.get("economy", _DEFAULT_CONFIG["economy"])

    @property
    def chat_config(self) -> dict[str, Any]:
        return self._config.get("chat", _DEFAULT_CONFIG["chat"])

    @property
    def command_config(self) -> dict[str, Any]:
        return self._config.get("commands", _DEFAULT_CONFIG["commands"])

    @property
    def performance_config(self) -> dict[str, Any]:
        return self._config.get("performance", _DEFAULT_CONFIG["performance"])

    @property
    def rtp_config(self) -> dict[str, Any]:
        return self._config.get("rtp", _DEFAULT_CONFIG["rtp"])

    @property
    def jail_config(self) -> dict[str, Any]:
        return self._config.get("jail", _DEFAULT_CONFIG["jail"])

    @property
    def scoreboard_config(self) -> dict[str, Any]:
        return self._config.get("scoreboard", self._scoreboard_defaults)

    @property
    def bossbar_config(self) -> dict[str, Any]:
        return self._config.get("bossbar", self._bossbar_defaults)

    @property
    def debug(self) -> bool:
        return self._config.get("debug", False)

    def load_all(
        self,
        scoreboard_defaults: dict | None = None,
        bossbar_defaults: dict | None = None,
    ) -> None:
        self._data_folder.mkdir(parents=True, exist_ok=True)

        self._scoreboard_defaults = scoreboard_defaults or {}
        self._bossbar_defaults = bossbar_defaults or {}

        self._config = self._load_yaml("config.yml", _DEFAULT_CONFIG)

        # xóa key cũ nếu config.yml từng chứa
        self._config.pop("scoreboard", None)
        self._config.pop("bossbar", None)

        self._load_separate(
            "scoreboard.yml",
            "scoreboard",
            self._scoreboard_defaults,
        )

        self._load_separate(
            "bossbar.yml",
            "bossbar",
            self._bossbar_defaults,
        )

    def _load_separate(
        self,
        filename: str,
        key: str,
        resource_defaults: dict | None = None,
    ) -> None:
        defaults = resource_defaults or {}
        filepath = self._data_folder / filename

        if not filepath.exists():
            self._save_yaml(filepath, defaults)
            self._config[key] = dict(defaults)
            return

        try:
            with filepath.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                self._logger.warning(f"Invalid {filename}, using defaults.")
                self._config[key] = dict(defaults)
                return

            self._config[key] = self._deep_merge(dict(defaults), data)

        except Exception as e:
            self._logger.error(f"Error loading {filename}: {e}")
            self._config[key] = dict(defaults)

    def reload(self) -> None:
        self.load_all(self._scoreboard_defaults, self._bossbar_defaults)

    def _load_yaml(self, filename: str, defaults: dict) -> dict:
        filepath = self._data_folder / filename

        if not filepath.exists():
            self._save_yaml(filepath, defaults)
            return dict(defaults)

        try:
            with filepath.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                self._logger.warning(f"Invalid {filename}, using defaults.")
                return dict(defaults)

            return self._deep_merge(defaults, data)

        except Exception as e:
            self._logger.error(f"Error loading {filename}: {e}")
            return dict(defaults)

    def _save_yaml(self, filepath: Path, data: dict) -> None:
        try:
            with filepath.open("w", encoding="utf-8") as f:
                yaml.dump(
                    data,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                )
        except Exception as e:
            self._logger.error(f"Error saving {filepath.name}: {e}")

    @staticmethod
    def _deep_merge(defaults: dict, overrides: dict) -> dict:
        result = dict(defaults)

        for key, value in overrides.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = ConfigLoader._deep_merge(result[key], value)
            else:
                result[key] = value

        return result