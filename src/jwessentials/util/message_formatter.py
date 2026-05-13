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
    "join-message": "&e{player} joined the server.",
    "first-join-message": "&dWelcome {player} to the server for the first time!",
    "quit-message": "&e{player} left the server.",
    "death-default": "&c☠ &7{message}",
    "death-fall": "&c{player} fell from a high place.",
    "death-lava": "&c{player} tried to swim in lava.",
    "death-drowning": "&c{player} drowned.",
    "death-suffocation": "&c{player} suffocated.",
    "death-fire": "&c{player} went up in flames.",
    "death-fire_tick": "&c{player} burned to death.",
    "death-starve": "&c{player} starved to death.",
    "death-entity_attack": "&c{player} was slain by {killer}.",
    "death-projectile": "&c{player} was shot by {killer}.",
    "death-entity_explosion": "&c{player} was blown up by {killer}.",
    "death-block_explosion": "&c{player} blew up (possibly from a bed explosion).",
    "death-freezing": "&c{player} froze to death.",
    "death-lightning": "&c{player} was struck by lightning.",
    "death-magic": "&c{player} was killed by magic.",
    "death-wither": "&c{player} withered away.",
    "death-void": "&c{player} fell out of the world.",
    "death-suicide": "&c{player} died by suicide.",
    "death-fly_into_wall": "&c{player} flew into a wall.",
    "death-thorns": "&c{player} was killed trying to hurt {killer}.",
    "death-sonic_boom": "&c{player} was obliterated by Warden's sonic boom.",
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
