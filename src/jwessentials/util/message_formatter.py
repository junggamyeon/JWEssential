from __future__ import annotations

from typing import Any

from jwessentials.util.config_loader import ConfigLoader as _ConfigLoader


_DEFAULT_MESSAGES = {
    "prefix": "&6&l[JWEssentials]&r ",
    "error-generic": "{prefix}&cAn internal error occurred. Please try again.",
    "player-only": "{prefix}&cThis command can only be used by players.",
    "no-permission": "{prefix}&cYou do not have permission to do that.",
    "invalid-arguments": "{prefix}&cInvalid arguments. Usage: {usage}",
    "player-not-found": "{prefix}&cPlayer not found: {player}",
    "teleport-sent": "{prefix}&aTeleporting to {player}...",
    "teleport-player-sent": "{prefix}&aTeleporting {player} to {target}...",
    "home-set": "{prefix}&aHome '{name}' set.",
    "home-teleported": "{prefix}&aTeleporting to home '{name}'...",
    "warp-teleported": "{prefix}&aWarping to '{name}'...",
    "spawn-teleported": "{prefix}&aTeleporting to spawn...",
}


class MessageFormatter:

    def __init__(self, messages: dict[str, str]) -> None:
        self._messages = messages
        self._prefix = self._get_raw("prefix", "&6&l[JWEssentials]&r ")

    def _get_raw(self, key: str, fallback: str = "") -> str:
        return self._messages.get(key, fallback)

    def format(self, key: str, **kwargs: Any) -> str:
        raw = self._messages.get(key)
        if raw is None:
            return f"§cMissing message: {key}"
        template = raw
        kwargs.setdefault("prefix", self._prefix)
        try:
            result = template.format(**kwargs)
        except (KeyError, ValueError):
            return template
        return self._translate_colors(result)

    def format_motd(self, template: str) -> str:
        return self._translate_colors(template)

    def _translate_colors(self, text: str) -> str:
        return text.replace("&", "§")

    def reload(self, messages: dict[str, str]) -> None:
        self._messages = messages
        self._prefix = self._get_raw("prefix", "&6&l[JWEssentials]&r ")

    @property
    def prefix(self) -> str:
        return self._translate_colors(self._prefix)
