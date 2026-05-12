from __future__ import annotations

from typing import TYPE_CHECKING

from endstone import Player
from endstone.command import CommandSender
from endstone.level import Location

if TYPE_CHECKING:
    from jwessentials.main import JWEssentials


class TeleportCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.msg("player-only"))
            return True

        if len(args) == 0:
            sender.send_message("§c/tp <player> [target]")
            sender.send_message("§c/tp <x> <y> <z> [world]")
            return True

        if len(args) == 1:
            self._teleport_to_player(sender, args[0])
        elif len(args) == 2:
            self._teleport_player_to_player(sender, args[0], args[1])
        elif len(args) >= 4:
            self._teleport_to_coords(sender, args)
        else:
            sender.send_message("§c/tp <player> [target]  or  /tp <x> <y> <z> [world]")
        return True

    def _teleport_to_player(self, sender: Player, target_name: str) -> None:
        target = self._plugin.server.get_player(target_name)
        if target is None:
            sender.send_message(self._plugin.msg("player-not-found", player=target_name))
            return

        sender.send_message(self._plugin.msg("teleport-sent", player=target.name))
        sender.teleport(target.location)

    def _teleport_player_to_player(self, sender: CommandSender, who_name: str, target_name: str) -> None:
        target = self._plugin.server.get_player(target_name)
        if target is None:
            sender.send_message(self._plugin.msg("player-not-found", player=target_name))
            return

        who = self._plugin.server.get_player(who_name)
        if who is None:
            sender.send_message(self._plugin.msg("player-not-found", player=who_name))
            return

        sender.send_message(self._plugin.msg("teleport-player-sent", player=who.name, target=target_name))
        who.teleport(target.location)

    def _teleport_to_coords(self, sender: Player, args: list[str]) -> None:
        try:
            x = float(args[0])
            y = float(args[1])
            z = float(args[2])
        except ValueError:
            sender.send_message(self._plugin.msg("tp-no-coordinate"))
            return

        world_id = args[3] if len(args) >= 4 else str(sender.location.dimension)
        dim = sender.location.level.get_dimension(world_id)
        if dim is None:
            sender.send_message(self._plugin.msg("tp-invalid-world", world=world_id))
            return

        loc = Location(dim, x, y, z, sender.location.pitch, sender.location.yaw)
        sender.send_message(self._plugin.msg("teleport-pos-sent", x=int(x), y=int(y), z=int(z), world=world_id))
        sender.teleport(loc)
