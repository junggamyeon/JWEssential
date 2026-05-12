from __future__ import annotations

import re
from typing import TYPE_CHECKING

from endstone.scoreboard import Criteria, DisplaySlot, ObjectiveSortOrder, RenderType

if TYPE_CHECKING:
    from jwessentials.main import JWEssentials


_PLAYER_PLACEHOLDERS = {
    "%player_name%": lambda p, _: p.name,
    "%player_xuid%": lambda p, _: p.xuid,
    "%player_uuid%": lambda p, _: str(p.unique_id),
    "%player_health%": lambda p, _: int(p.health),
    "%player_max_health%": lambda p, _: int(p.max_health),
    "%player_level%": lambda p, _: p.exp_level,
    "%player_exp%": lambda p, _: p.total_exp,
    "%player_ping%": lambda p, _: p.ping,
    "%player_world%": lambda p, _: p.level.name,
    "%player_dimension%": lambda p, _: p.dimension.name,
    "%player_gamemode%": lambda p, _: str(p.game_mode).split(".")[-1].lower(),
    "%player_x%": lambda p, _: int(p.location.x),
    "%player_y%": lambda p, _: int(p.location.y),
    "%player_z%": lambda p, _: int(p.location.z),
    "%player_is_flying%": lambda p, _: str(p.is_flying).lower(),
    "%player_is_sneaking%": lambda p, _: str(p.is_sneaking).lower(),
    "%player_is_op%": lambda p, _: str(p.is_op).lower(),
    "%n%": lambda p, _: p.name,
    "%id%": lambda p, _: p.xuid,
    "%uid%": lambda p, _: str(p.unique_id),
    "%hp%": lambda p, _: int(p.health),
    "%mhp%": lambda p, _: int(p.max_health),
    "%lv%": lambda p, _: p.exp_level,
    "%xp%": lambda p, _: p.total_exp,
    "%pg%": lambda p, _: p.ping,
    "%w%": lambda p, _: p.level.name,
    "%dim%": lambda p, _: p.dimension.name,
    "%gm%": lambda p, _: str(p.game_mode).split(".")[-1].lower(),
    "%x%": lambda p, _: int(p.location.x),
    "%y%": lambda p, _: int(p.location.y),
    "%z%": lambda p, _: int(p.location.z),
    "%fly%": lambda p, _: str(p.is_flying).lower(),
    "%snk%": lambda p, _: str(p.is_sneaking).lower(),
    "%op%": lambda p, _: str(p.is_op).lower(),
}

_SERVER_PLACEHOLDERS = {
    "%server_name%": lambda p, s: s.name,
    "%server_version%": lambda p, s: s.version,
    "%server_mc_version%": lambda p, s: s.minecraft_version,
    "%server_online%": lambda p, s: len(s.online_players),
    "%server_max_players%": lambda p, s: s.max_players,
    "%server_port%": lambda p, s: s.port,
    "%sn%": lambda p, s: s.name,
    "%sv%": lambda p, s: s.version,
    "%mc%": lambda p, s: s.minecraft_version,
    "%on%": lambda p, s: len(s.online_players),
    "%max%": lambda p, s: s.max_players,
    "%pt%": lambda p, s: s.port,
}

def _resolve(text: str, player, server) -> str:
    if not isinstance(text, str):
        return str(text) if text else ""
    result = text
    for ph, fn in {**_PLAYER_PLACEHOLDERS, **_SERVER_PLACEHOLDERS}.items():
        if ph in result:
            try:
                result = result.replace(ph, str(fn(player, server)))
            except Exception:
                result = result.replace(ph, "?")
    return result


def _strip_color(text: str) -> str:
    if not isinstance(text, str):
        return str(text)
    return re.sub(r"§[0-9a-fr]", "", text)


class ScoreboardHandler:
    """Per-player scoreboard: each player gets their own isolated Scoreboard
    created via ``server.create_scoreboard()``, so no player ever sees another
    player's sidebar content.  Follows the ScoreHud C++ reference pattern."""

    _OBJ_NAME = "jw_sb"

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin
        # uuid -> {"scoreboard": Scoreboard, "objective": Objective}
        self._sessions: dict = {}
        self._lines: list[str] = []
        self._display_name: str = ""
        self._slot: DisplaySlot = DisplaySlot.SIDE_BAR
        self._ascending: bool = True
        self._enabled: bool = False

    @property
    def _config(self) -> dict:
        return self._plugin._config_loader.scoreboard_config

    def load(self) -> None:
        cfg = self._config
        if not cfg.get("enabled", False):
            self.disable()
            return

        self._display_name = cfg.get("display-name", "§6§lInfo")
        slot_str = cfg.get("slot", "sidebar").lower()
        self._slot = {
            "sidebar": DisplaySlot.SIDE_BAR,
            "list": DisplaySlot.PLAYER_LIST,
            "belowname": DisplaySlot.BELOW_NAME,
        }.get(slot_str, DisplaySlot.SIDE_BAR)

        self._ascending = cfg.get("ascending", True)
        self._lines = [line for line in cfg.get("lines", []) if line is not False]
        self._enabled = True

        self._schedule_update()

    # -- session lifecycle ---------------------------------------------------

    def _create_session(self, player):
        """Create an isolated scoreboard for *player* and assign it."""
        uid = player.unique_id

        # Tear down previous session (if any) before creating a new one
        self._destroy_session(player)

        # Create a brand-new scoreboard that only this player will see
        scoreboard = self._plugin.server.create_scoreboard()
        player.scoreboard = scoreboard

        sort_order = (
            ObjectiveSortOrder.ASCENDING
            if self._ascending
            else ObjectiveSortOrder.DESCENDING
        )

        objective = scoreboard.add_objective(
            self._OBJ_NAME,
            Criteria.DUMMY,
            _strip_color(self._display_name),
            RenderType.INTEGER,
        )
        objective.set_display(self._slot, sort_order)

        self._sessions[uid] = {
            "scoreboard": scoreboard,
            "objective": objective,
        }

    def _destroy_session(self, player):
        """Remove the player's private scoreboard and restore the server one."""
        session = self._sessions.pop(player.unique_id, None)
        if session is not None:
            try:
                session["scoreboard"].clear_slot(self._slot)
            except Exception:
                pass
        # Restore the server's default scoreboard
        try:
            player.scoreboard = self._plugin.server.scoreboard
        except Exception:
            pass

    # -- update logic --------------------------------------------------------

    def _update_player(self, player):
        uid = player.unique_id
        session = self._sessions.get(uid)
        if session is None:
            self._create_session(player)
            session = self._sessions.get(uid)
            if session is None:
                return

        scoreboard = session["scoreboard"]
        objective = session["objective"]
        server = self._plugin.server

        # Update display name (supports flicker titles later)
        try:
            objective.display_name = _strip_color(self._display_name)
        except Exception:
            pass

        # Clear old entries
        try:
            for entry in list(scoreboard.entries):
                scoreboard.reset_scores(entry)
        except Exception:
            pass

        total = len(self._lines)

        for i, raw_line in enumerate(self._lines):
            text = _resolve(raw_line, player, server)
            entry = _strip_color(text)

            # Avoid duplicate lines by appending invisible spaces
            entry = entry + (" " * i)

            try:
                score = objective.get_score(entry)
                score.value = total - i
            except Exception:
                pass

    # -- scheduling ----------------------------------------------------------

    def _schedule_update(self):
        def task():
            if not self._enabled:
                return
            for player in list(self._plugin.server.online_players):
                try:
                    self._update_player(player)
                except Exception:
                    pass

            self._plugin.server.scheduler.run_task(
                self._plugin, task, delay=20
            )

        self._plugin.server.scheduler.run_task(self._plugin, task, delay=20)

    # -- public API ----------------------------------------------------------

    def enable(self):
        self.load()

    def disable(self):
        self._enabled = False
        for player in list(self._plugin.server.online_players):
            try:
                self._destroy_session(player)
            except Exception:
                pass
        self._sessions.clear()

    def on_player_join(self, player):
        if not self._enabled:
            return
        self._create_session(player)
        self._update_player(player)

    def on_player_quit(self, player):
        self._destroy_session(player)