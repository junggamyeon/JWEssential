from __future__ import annotations

from typing import TYPE_CHECKING

from endstone import Player
from endstone.command import CommandSender

if TYPE_CHECKING:
    from jwessentials.main import JWEssentials


class ReplyCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not args:
            sender.send_message("§c/jwr <message...>")
            return True

        last_target = self._plugin._last_replier.get(sender.name.lower())
        if not last_target:
            sender.send_message(self._plugin.msg("reply-no-one"))
            return True

        msg_handler = MsgCommandHandler(self._plugin)
        return msg_handler.handle(sender, [last_target] + args)


class MsgCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if len(args) < 2:
            sender.send_message("§c/jwmsg <player> <message...>")
            return True

        target_name = args[0]
        message = " ".join(args[1:])

        target = self._plugin.server.get_player(target_name)
        if target is None:
            sender.send_message(self._plugin.msg("player-not-found", player=target_name))
            return True

        sender_display = sender.name
        target_display = target.name
        formatted = self._plugin.msg(
            "msg-format",
            sender=sender_display,
            receiver=target_display,
            message=message,
        )

        sender.send_message(formatted)
        target.send_message(formatted)

        for player in self._plugin.server.online_players:
            if player.name.lower() != sender.name.lower() and player.name.lower() != target.name.lower():
                if str(player.unique_id) in self._plugin._socialspy_cache:
                    player.send_message(f"§8[SocialSpy] §7{sender_display} -> {target_display}: {message}")

        self._plugin._last_replier[sender.name.lower()] = target.name.lower()
        self._plugin._last_replier[target.name.lower()] = sender.name.lower()
        return True


class SocialSpyCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.msg("player-only"))
            return True

        async def task():
            try:
                uuid = str(sender.unique_id)
                enabled = await self._plugin._socialspy_repo.is_enabled(uuid)
                new_state = not enabled
                await self._plugin._socialspy_repo.set_enabled(uuid, new_state)
                self._plugin.cache_socialspy(uuid, new_state)

                def notify():
                    sender.send_message(
                        self._plugin.msg("social-spy-enabled") if new_state
                        else self._plugin.msg("social-spy-disabled")
                    )
                self._plugin.server.scheduler.run_task(self._plugin, notify)
            except Exception as e:
                self._plugin.logger.error(f"Social spy error: {e}")

        self._plugin.run_async(task())
        return True


class AfkCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.msg("player-only"))
            return True

        async def task():
            try:
                uuid = str(sender.unique_id)
                profile = await self._plugin._profile_repo.get_profile(uuid)
                is_afk = not profile.is_afk if profile else True

                await self._plugin._profile_repo.update_afk(uuid, is_afk)
                self._plugin._afk_players[sender.name.lower()] = is_afk

                def notify():
                    if is_afk:
                        sender.send_message(self._plugin.msg("afk-self"))
                        self._plugin.server.broadcast_message(
                            self._plugin.msg("afk-set", player=sender.name)
                        )
                    else:
                        sender.send_message(self._plugin.msg("afk-self-remove"))
                        self._plugin.server.broadcast_message(
                            self._plugin.msg("afk-removed", player=sender.name)
                        )
                self._plugin.server.scheduler.run_task(self._plugin, notify)
            except Exception as e:
                self._plugin.logger.error(f"AFK error: {e}")

        self._plugin.run_async(task())
        return True
