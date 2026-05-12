from __future__ import annotations

from typing import TYPE_CHECKING

from endstone import Player
from endstone.command import CommandSender
from endstone.level import Location

if TYPE_CHECKING:
    from jwessentials.main import JWEssentials


class TPACommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.msg("player-only"))
            return True

        if not args:
            sender.send_message("§c/tpa <player>")
            return True

        target_name = args[0]
        target = self._plugin.server.get_player(target_name)
        if target is None:
            sender.send_message(self._plugin.msg("player-not-found", player=target_name))
            return True

        if target.name.lower() == sender.name.lower():
            sender.send_message("§cYou cannot teleport to yourself.")
            return True

        sender_uuid = str(sender.unique_id)
        receiver_uuid = str(target.unique_id)
        target_display = target.name
        sender_display = sender.name

        async def task():
            try:
                has_active = await self._plugin._tpa_repo.has_active_request(sender_uuid, receiver_uuid)
                if has_active:
                    def notify():
                        sender.send_message(self._plugin.msg("tpa-already-sent", player=target_display))
                    self._plugin.server.scheduler.run_task(self._plugin, notify)
                    return

                await self._plugin._tpa_repo.create_request(
                    sender_uuid=sender_uuid,
                    sender_name=sender_display,
                    receiver_uuid=receiver_uuid,
                    receiver_name=target_display,
                )

                def notify_sender():
                    sender.send_message(self._plugin.msg("tpa-sent", player=target_display))

                def notify_target():
                    target.send_message(self._plugin.msg("tpa-received", player=sender_display))
                    target.send_message(self._plugin.msg("tpa-type-accept"))
                    target.send_message(self._plugin.msg("tpa-timeout-info", seconds=60))

                self._plugin.server.scheduler.run_task(self._plugin, notify_sender)
                self._plugin.server.scheduler.run_task(self._plugin, notify_target)
            except Exception as e:
                self._plugin.logger.error(f"TPA request error: {e}")

        self._plugin.run_async(task())
        return True


class TPAHereCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.msg("player-only"))
            return True

        if not args:
            sender.send_message("§c/tpahere <player>")
            return True

        target_name = args[0]
        target = self._plugin.server.get_player(target_name)
        if target is None:
            sender.send_message(self._plugin.msg("player-not-found", player=target_name))
            return True

        if target.name.lower() == sender.name.lower():
            sender.send_message("§cYou cannot teleport to yourself.")
            return True

        sender_uuid = str(sender.unique_id)
        receiver_uuid = str(target.unique_id)
        sender_location = sender.location
        target_display = target.name
        sender_display = sender.name

        async def task():
            try:
                has_active = await self._plugin._tpa_repo.has_active_request(sender_uuid, receiver_uuid)
                if has_active:
                    def notify():
                        sender.send_message(self._plugin.msg("tpa-already-sent", player=target_display))
                    self._plugin.server.scheduler.run_task(self._plugin, notify)
                    return

                await self._plugin._tpa_repo.create_request(
                    sender_uuid=receiver_uuid,
                    sender_name=target_display,
                    receiver_uuid=sender_uuid,
                    receiver_name=sender_display,
                    location=sender_location,
                )

                def notify_sender():
                    sender.send_message(self._plugin.msg("tpa-sent", player=target_display))

                def notify_target():
                    target.send_message(self._plugin.msg("tpa-received", player=sender_display))
                    target.send_message("§eType §a/tpaccept§e or §a/tpa§e to accept, §c/tpdeny§e to deny.")

                self._plugin.server.scheduler.run_task(self._plugin, notify_sender)
                self._plugin.server.scheduler.run_task(self._plugin, notify_target)
            except Exception as e:
                self._plugin.logger.error(f"TPAHere request error: {e}")

        self._plugin.run_async(task())
        return True


class TPAcceptCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.msg("player-only"))
            return True

        async def task():
            try:
                receiver_uuid = str(sender.unique_id)
                request = await self._plugin._tpa_repo.get_active_request_for_receiver(receiver_uuid)
                if request is None:
                    def notify():
                        sender.send_message(self._plugin.msg("tpa-no-request"))
                    self._plugin.server.scheduler.run_task(self._plugin, notify)
                    return

                sender_player = self._plugin.server.get_player(request.sender_name)
                if sender_player is None:
                    def notify():
                        sender.send_message(self._plugin.msg("player-not-found", player=request.sender_name))
                    self._plugin.server.scheduler.run_task(self._plugin, notify)
                    return

                def do_teleport():
                    sender.send_message(self._plugin.msg("tpa-accepted"))
                    if request.world and request.x is not None:
                        from endstone.level import Dimension
                        dim = self._plugin.server.level.get_dimension(request.world)
                        if dim:
                            from endstone.level import Location
                            loc = Location(
                                dim,
                                request.x,
                                request.y,
                                request.z,
                                request.pitch or 0,
                                request.yaw or 0,
                            )
                            sender_player.teleport(loc)
                            return
                    sender_player.teleport(sender.location)

                self._plugin.server.scheduler.run_task(self._plugin, do_teleport)

            except Exception as e:
                self._plugin.logger.error(f"TPAccept error: {e}")

        self._plugin.run_async(task())
        return True


class TPAcceptHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        return TPAcceptCommandHandler(self._plugin).handle(sender, args)


class TPAcDenyHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.msg("player-only"))
            return True

        async def task():
            try:
                receiver_uuid = str(sender.unique_id)
                request = await self._plugin._tpa_repo.get_active_request_for_receiver(receiver_uuid)
                if request is None:
                    def notify():
                        sender.send_message(self._plugin.msg("tpa-no-request"))
                    self._plugin.server.scheduler.run_task(self._plugin, notify)
                    return

                await self._plugin._tpa_repo.delete_request(request.id)

                def notify():
                    sender.send_message(self._plugin.msg("tpa-declined"))
                self._plugin.server.scheduler.run_task(self._plugin, notify)
            except Exception as e:
                self._plugin.logger.error(f"TPADeny error: {e}")

        self._plugin.run_async(task())
        return True


class TPAcCancelHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.msg("player-only"))
            return True

        async def task():
            try:
                sender_uuid = str(sender.unique_id)
                request = await self._plugin._tpa_repo.get_active_request_by_sender(sender_uuid)
                if request is None:
                    def notify():
                        sender.send_message(self._plugin.msg("tpa-no-request"))
                    self._plugin.server.scheduler.run_task(self._plugin, notify)
                    return

                await self._plugin._tpa_repo.delete_request(request.id)

                def notify():
                    sender.send_message(self._plugin.msg("tpa-cancelled"))
                self._plugin.server.scheduler.run_task(self._plugin, notify)
            except Exception as e:
                self._plugin.logger.error(f"TPAcancel error: {e}")

        self._plugin.run_async(task())
        return True


class TPOHereCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.msg("player-only"))
            return True

        if not args:
            sender.send_message(self._plugin.msg("tp-here-usage"))
            return True

        target = self._plugin.server.get_player(args[0])
        if target is None:
            sender.send_message(self._plugin.msg("player-not-found", player=args[0]))
            return True

        sender.send_message(self._plugin.msg("tp-here", player=target.name))

        def do_teleport():
            target.send_message(self._plugin.msg("tp-here", player=target.name))
            target.teleport(sender.location)

        self._plugin.server.scheduler.run_task(self._plugin, do_teleport)
        return True
