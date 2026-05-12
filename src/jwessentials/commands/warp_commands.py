from __future__ import annotations

from typing import TYPE_CHECKING

from endstone import Player
from endstone.command import CommandSender
from endstone.level import Location

if TYPE_CHECKING:
    from jwessentials.main import JWEssentials


class WarpCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if len(args) == 0:
            self._list_warps(sender)
            return True

        warp_name = args[0].lower()
        target_player = None
        if len(args) >= 2 and sender.has_permission("jwessentials.warp.others"):
            target_player = self._plugin.server.get_player(args[1])
            if target_player is None:
                sender.send_message(self._plugin.msg("player-not-found", player=args[1]))
                return True

        player = target_player if target_player else sender
        self._teleport_to_warp(sender, player, warp_name)
        return True

    def _teleport_to_warp(self, sender: CommandSender, player: Player, warp_name: str) -> None:
        sender.send_message(self._plugin.msg("warp-teleported", name=warp_name))
        async def task():
            try:
                warp = await self._plugin._warp_repo.get_warp(warp_name)
                if warp is None:
                    def notify():
                        sender.send_message(self._plugin.msg("warp-not-found", name=warp_name))
                    self._plugin.server.scheduler.run_task(self._plugin, notify)
                    return

                dim = self._plugin.server.level.get_dimension(warp.world)
                if dim is None:
                    def notify():
                        sender.send_message(self._plugin.msg("tp-invalid-world", world=warp.world))
                    self._plugin.server.scheduler.run_task(self._plugin, notify)
                    return

                def do_teleport():
                    loc = Location(dim, warp.x, warp.y, warp.z, warp.pitch, warp.yaw)
                    player.teleport(loc)
                self._plugin.server.scheduler.run_task(self._plugin, do_teleport)
            except Exception as e:
                self._plugin.logger.error(f"Warp teleport error: {e}")

        self._plugin.run_async(task())

    def _list_warps(self, sender: CommandSender) -> None:
        async def task():
            try:
                warps = await self._plugin._warp_repo.get_all_warps()
                if not warps:
                    def notify():
                        sender.send_message(self._plugin.msg("warp-no-warps"))
                    self._plugin.server.scheduler.run_task(self._plugin, notify)
                    return
                warp_names = ", ".join(w.name for w in warps)

                def notify():
                    sender.send_message(self._plugin.msg("warp-list-header"))
                    sender.send_message(self._plugin.msg("warp-list", warps=warp_names))
                self._plugin.server.scheduler.run_task(self._plugin, notify)
            except Exception as e:
                self._plugin.logger.error(f"List warps error: {e}")

        self._plugin.run_async(task())


class SetWarpCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.msg("player-only"))
            return True

        if not args:
            sender.send_message("§c/jwsetwarp <name>")
            return True

        warp_name = args[0].lower()
        sender_loc = sender.location
        sender_dim_id = sender_loc.dimension.name

        async def task():
            try:
                await self._plugin._warp_repo.set_warp(warp_name, sender_loc, created_by=sender.name)

                def notify():
                    sender.send_message(
                        self._plugin.msg(
                            "warp-set",
                            name=warp_name,
                            world=sender_dim_id,
                            x=int(sender_loc.x),
                            y=int(sender_loc.y),
                            z=int(sender_loc.z),
                        )
                    )
                self._plugin.server.scheduler.run_task(self._plugin, notify)
            except Exception as e:
                self._plugin.logger.error(f"Set warp error: {e}")

        self._plugin.run_async(task())
        return True


class DelWarpCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not args:
            sender.send_message("§c/jwdelwarp <name>")
            return True

        warp_name = args[0].lower()

        async def task():
            try:
                deleted = await self._plugin._warp_repo.delete_warp(warp_name)

                def notify():
                    if deleted:
                        sender.send_message(self._plugin.msg("warp-deleted", name=warp_name))
                    else:
                        sender.send_message(self._plugin.msg("warp-not-found", name=warp_name))
                self._plugin.server.scheduler.run_task(self._plugin, notify)
            except Exception as e:
                self._plugin.logger.error(f"Delete warp error: {e}")

        self._plugin.run_async(task())
        return True
