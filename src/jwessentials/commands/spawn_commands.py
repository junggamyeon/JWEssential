from __future__ import annotations

from typing import TYPE_CHECKING

from endstone import Player
from endstone.command import CommandSender
from endstone.level import Dimension, Location

if TYPE_CHECKING:
    from jwessentials.main import JWEssentials


class SpawnCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        player = sender
        if len(args) >= 1 and sender.has_permission("jwessentials.spawn.others"):
            target = self._plugin.server.get_player(args[0])
            if target:
                player = target
            else:
                sender.send_message(self._plugin.msg("player-not-found", player=args[0]))
                return True

        sender.send_message(self._plugin.msg("spawn-teleported"))
        async def task():
            try:
                spawn = await self._plugin._spawn_repo.get_spawn()
                if spawn is None:
                    def notify():
                        sender.send_message(self._plugin.msg("spawn-not-set"))
                    self._plugin.server.scheduler.run_task(self._plugin, notify)
                    return

                dim = self._plugin.server.level.get_dimension(spawn.world)
                if dim is None:
                    def notify():
                        sender.send_message(self._plugin.msg("tp-invalid-world", world=spawn.world))
                    self._plugin.server.scheduler.run_task(self._plugin, notify)
                    return

                def do_teleport():
                    loc = Location(dim, spawn.x, spawn.y, spawn.z, spawn.pitch, spawn.yaw)
                    player.teleport(loc)
                self._plugin.server.scheduler.run_task(self._plugin, do_teleport)
            except Exception as e:
                self._plugin.logger.error(f"Spawn teleport error: {e}")

        self._plugin.run_async(task())
        return True


class SetSpawnCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.msg("player-only"))
            return True

        async def task():
            try:
                await self._plugin._spawn_repo.set_spawn(sender.location)

                def notify():
                    sender.send_message(self._plugin.msg("spawn-set"))
                self._plugin.server.scheduler.run_task(self._plugin, notify)
            except Exception as e:
                self._plugin.logger.error(f"Set spawn error: {e}")

        self._plugin.run_async(task())
        return True
