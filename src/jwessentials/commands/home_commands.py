from __future__ import annotations

from typing import TYPE_CHECKING

from endstone import Player
from endstone.command import CommandSender
from endstone.level import Location

if TYPE_CHECKING:
    from jwessentials.main import JWEssentials


class HomeCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.msg("player-only"))
            return True

        home_name = args[0] if args else "home"

        sender.send_message(self._plugin.msg("home-teleported", name=home_name))
        async def task():
            try:
                home_data = await self._plugin._home_repo.get_home(str(sender.unique_id), home_name)
                if home_data is None:
                    def notify():
                        sender.send_message(self._plugin.msg("home-not-found", name=home_name))
                    self._plugin.server.scheduler.run_task(self._plugin, notify)
                    return

                dim = self._plugin.server.level.get_dimension(home_data.world)
                if dim is None:
                    def notify():
                        sender.send_message(self._plugin.msg("tp-invalid-world", world=home_data.world))
                    self._plugin.server.scheduler.run_task(self._plugin, notify)
                    return

                def do_teleport():
                    loc = Location(dim, home_data.x, home_data.y, home_data.z, home_data.pitch, home_data.yaw)
                    success = sender.teleport(loc)
                    if not success:
                        sender.send_message(self._plugin.msg("error-generic"))
                self._plugin.server.scheduler.run_task(self._plugin, do_teleport)
            except Exception as e:
                self._plugin.logger.error(f"Home teleport error: {e}")

        self._plugin.run_async(task())
        return True

    def list_homes(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.msg("player-only"))
            return True

        async def task():
            try:
                homes = await self._plugin._home_repo.get_homes(str(sender.unique_id))
                if not homes:
                    def notify():
                        sender.send_message(self._plugin.msg("home-no-homes"))
                    self._plugin.server.scheduler.run_task(self._plugin, notify)
                    return
                home_names = ", ".join(h.name for h in homes)

                def notify():
                    sender.send_message(self._plugin.msg("home-list", homes=home_names))
                self._plugin.server.scheduler.run_task(self._plugin, notify)
            except Exception as e:
                self._plugin.logger.error(f"List homes error: {e}")

        self._plugin.run_async(task())
        return True


class SetHomeCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.msg("player-only"))
            return True

        home_name = args[0] if args else "home"
        player_uuid = str(sender.unique_id)
        sender_loc = sender.location
        sender_dim_id = sender_loc.dimension.name

        async def task():
            try:
                count = await self._plugin._home_repo.count_homes(player_uuid)
                limit = self._plugin.get_home_limit(sender)

                if count >= limit and not await self._plugin._home_repo.home_exists(player_uuid, home_name):
                    def notify():
                        sender.send_message(self._plugin.msg("home-limit-reached", limit=limit))
                    self._plugin.server.scheduler.run_task(self._plugin, notify)
                    return

                await self._plugin._home_repo.set_home(player_uuid, home_name, sender_loc)

                def notify():
                    sender.send_message(
                        self._plugin.msg(
                            "home-set",
                            name=home_name,
                            world=sender_dim_id,
                            x=int(sender_loc.x),
                            y=int(sender_loc.y),
                            z=int(sender_loc.z),
                        )
                    )
                self._plugin.server.scheduler.run_task(self._plugin, notify)
            except Exception as e:
                self._plugin.logger.error(f"Set home error: {e}")

        self._plugin.run_async(task())
        return True


class DelHomeCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.msg("player-only"))
            return True

        if not args:
            sender.send_message(self._plugin.msg("sethome-usage"))
            return True

        home_name = args[0]
        player_uuid = str(sender.unique_id)

        async def task():
            try:
                deleted = await self._plugin._home_repo.delete_home(player_uuid, home_name)

                def notify():
                    if deleted:
                        sender.send_message(self._plugin.msg("home-deleted", name=home_name))
                    else:
                        sender.send_message(self._plugin.msg("home-not-found", name=home_name))
                self._plugin.server.scheduler.run_task(self._plugin, notify)
            except Exception as e:
                self._plugin.logger.error(f"Delete home error: {e}")

        self._plugin.run_async(task())
        return True
