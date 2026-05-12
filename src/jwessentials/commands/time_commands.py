from __future__ import annotations

from typing import TYPE_CHECKING

from endstone import Player
from endstone.command import CommandSender

if TYPE_CHECKING:
    from jwessentials.main import JWEssentials


_TIME_KEYWORDS = {
    "day": 1000,
    "noon": 6000,
    "sunset": 12000,
    "dusk": 12500,
    "night": 14000,
    "midnight": 18000,
    "sunrise": 23000,
    "dawn": 23000,
}


class TimeCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if len(args) < 1:
            sender.send_message("§c/jwwtime set <time|day|noon|night|midnight>")
            sender.send_message("§c/jwwtime add <ticks>")
            return True

        action = args[0].lower()
        if action == "set":
            self._handle_set(sender, args[1:] if len(args) > 1 else [])
        elif action == "add":
            self._handle_add(sender, args[1:] if len(args) > 1 else [])
        else:
            self._handle_set(sender, args)
        return True

    def _handle_set(self, sender: CommandSender, args: list[str]) -> None:
        if not args:
            sender.send_message("§c/jwwtime set <time|day|noon|night|midnight>")
            return

        raw = args[0].lower()
        ticks = self._parse_time(raw)
        if ticks is None:
            sender.send_message(self._plugin.msg("ptime-invalid"))
            return

        level = self._plugin.server.level
        level.time = ticks
        sender.send_message(self._plugin.msg("time-set", time=raw))

    def _handle_add(self, sender: CommandSender, args: list[str]) -> None:
        if not args:
            sender.send_message("§c/jwwtime add <ticks>")
            return

        try:
            ticks = int(args[0])
        except ValueError:
            sender.send_message(self._plugin.msg("ptime-invalid"))
            return

        level = self._plugin.server.level
        level.time = (level.time + ticks) % 24000
        sender.send_message(self._plugin.msg("time-set", time=f"+{ticks}"))

    @staticmethod
    def _parse_time(raw: str) -> int | None:
        if raw in _TIME_KEYWORDS:
            return _TIME_KEYWORDS[raw]
        try:
            return int(raw) % 24000
        except ValueError:
            return None


class PTimeCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.msg("player-only"))
            return True

        if len(args) < 1:
            sender.send_message("§c/jwptime <set|reset|day|noon|night|get> [player]")
            return True

        action = args[0].lower()
        target_name = None
        if len(args) >= 2:
            if sender.has_permission("jwessentials.ptime.others"):
                target_name = args[1]
            else:
                sender.send_message(self._plugin.msg("ptime-others-perm"))
                return True

        if action == "get":
            self._handle_get(sender, target_name)
        elif action == "reset":
            self._handle_reset(sender, target_name)
        elif action == "set":
            if len(args) >= 2:
                self._handle_set(sender, target_name, args[1])
            else:
                sender.send_message("§c/jwptime set <day|noon|night|midnight|ticks>")
        else:
            self._handle_set(sender, target_name, action)

        return True

    def _handle_get(self, sender: CommandSender, target_name: str | None) -> None:
        target = sender
        if target_name:
            t = self._plugin.server.get_player(target_name)
            if t:
                target = t

        async def task():
            try:
                profile = await self._plugin._profile_repo.get_profile(str(target.unique_id))
                time_val = profile.personal_time if profile else None

                def notify():
                    msg = (
                        self._plugin.msg("ptime-normal", player=target.name)
                        if time_val is None
                        else self._plugin.msg("ptime-get", player=target.name, time=str(time_val))
                    )
                    sender.send_message(msg)
                self._plugin.server.scheduler.run_task(self._plugin, notify)
            except Exception as e:
                self._plugin.logger.error(f"PTime get error: {e}")

        self._plugin.run_async(task())

    def _handle_reset(self, sender: CommandSender, target_name: str | None) -> None:
        target = sender
        if target_name:
            t = self._plugin.server.get_player(target_name)
            if t:
                target = t

        async def task():
            try:
                await self._plugin._profile_repo.update_personal_time(str(target.unique_id), None)

                def notify():
                    sender.send_message(self._plugin.msg("ptime-reset"))
                self._plugin.server.scheduler.run_task(self._plugin, notify)
            except Exception as e:
                self._plugin.logger.error(f"PTime reset error: {e}")

        self._plugin.run_async(task())

    def _handle_set(self, sender: CommandSender, target_name: str | None, time_str: str) -> None:
        target = sender
        if target_name:
            t = self._plugin.server.get_player(target_name)
            if t:
                target = t

        ticks = TimeCommandHandler._parse_time(time_str.lower())
        if ticks is None:
            sender.send_message(self._plugin.msg("ptime-invalid"))
            return

        async def task():
            try:
                await self._plugin._profile_repo.update_personal_time(str(target.unique_id), ticks)

                def notify():
                    sender.send_message(self._plugin.msg("ptime-set", player=target.name, time=time_str))
                self._plugin.server.scheduler.run_task(self._plugin, notify)
            except Exception as e:
                self._plugin.logger.error(f"PTime set error: {e}")

        self._plugin.run_async(task())


class WeatherCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.msg("player-only"))
            return True

        if not args:
            sender.send_message("§c/jwweather <sun|rain|thunder|clear>")
            return True

        weather_type = args[0].lower()
        if weather_type in ("sun", "clear"):
            weather_type = "clear"
        elif weather_type in ("rain", "downfall"):
            weather_type = "rain"
        elif weather_type not in ("rain", "thunder", "clear"):
            sender.send_message("§cInvalid weather type. Use: sun, rain, thunder, clear")
            return True

        sender.send_message(self._plugin.msg("weather-set", weather=weather_type))
        return True


class TopCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.msg("player-only"))
            return True

        player: Player = sender
        loc = player.location
        dim = loc.dimension

        top_y = dim.get_highest_block_y_at(int(loc.x), int(loc.z))
        if top_y <= loc.y:
            sender.send_message("§cYou are already at the top.")
            return True

        from endstone.level import Location
        target_loc = Location(dim, loc.x, top_y + 1, loc.z, -90.0, 0.0)
        sender.teleport(target_loc)
        sender.send_message(f"§aTeleported to the top at Y={top_y + 1}.")
        return True


class JumpCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.msg("player-only"))
            return True

        player: Player = sender
        loc = player.location
        dim = loc.dimension

        target_y = loc.y - 1
        from endstone.level import Location
        target_loc = Location(dim, loc.x, target_y, loc.z, loc.pitch, loc.yaw)
        player.teleport(target_loc)
        sender.send_message("§aTeleported down one block.")
        return True
