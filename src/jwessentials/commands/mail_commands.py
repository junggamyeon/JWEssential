from __future__ import annotations

from typing import TYPE_CHECKING

from endstone import Player
from endstone.command import CommandSender

if TYPE_CHECKING:
    from jwessentials.main import JWEssentials


class MailCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.msg("player-only"))
            return True

        if not args:
            sender.send_message("§e/jmail read §7- Read your mail")
            sender.send_message("§e/jmail send <player> <message> §7- Send mail")
            sender.send_message("§e/jmail clear §7- Clear your mail")
            return True

        sub = args[0].lower()
        if sub == "read":
            self._handle_read(sender)
        elif sub == "send":
            self._handle_send(sender, args[1:])
        elif sub == "clear":
            self._handle_clear(sender)
        else:
            sender.send_message("§c/jmail read §c/send §c/clear")
        return True

    def _handle_read(self, sender: Player) -> None:
        async def task():
            try:
                mails = await self._plugin._mail_repo.get_unread_mail(str(sender.unique_id))
                if not mails:
                    def notify():
                        sender.send_message(self._plugin.msg("mail-no-mail"))
                    self._plugin.server.scheduler.run_task(self._plugin, notify)
                    return

                def notify_header():
                    sender.send_message(self._plugin.msg("mail-read-header"))

                self._plugin.server.scheduler.run_task(self._plugin, notify_header)
                for mail in mails[:10]:
                    def notify_mail():
                        sender.send_message(f"§e[{mail.sender_name}]§f: {mail.message}")
                    self._plugin.server.scheduler.run_task(self._plugin, notify_mail)
                    await self._plugin._mail_repo.mark_as_read(mail.id)
            except Exception as e:
                self._plugin.logger.error(f"Mail read error: {e}")

        self._plugin.run_async(task())

    def _handle_send(self, sender: Player, args: list[str]) -> None:
        if len(args) < 2:
            sender.send_message("§c/jmail send <player> <message>")
            return

        target_name = args[0]
        message = " ".join(args[1:])

        if len(message) > 500:
            sender.send_message("§cMessage too long (max 500 characters).")
            return

        target = self._plugin.server.get_player(target_name)
        initial_target_uuid = str(target.unique_id) if target else None
        initial_target_name = target.name if target else target_name

        async def task():
            try:
                target_uuid = initial_target_uuid
                if not target_uuid:
                    target_uuid = await self._plugin._profile_repo.get_uuid_by_name(initial_target_name)

                if not target_uuid:
                    def notify():
                        sender.send_message(self._plugin.msg("player-not-found", player=initial_target_name))
                    self._plugin.server.scheduler.run_task(self._plugin, notify)
                    return

                await self._plugin._mail_repo.send_mail(
                    receiver_uuid=target_uuid,
                    message=message,
                    sender_uuid=str(sender.unique_id),
                    sender_name=sender.name,
                )

                def notify():
                    sender.send_message(self._plugin.msg("mail-sent", player=initial_target_name))
                self._plugin.server.scheduler.run_task(self._plugin, notify)
            except Exception as e:
                self._plugin.logger.error(f"Mail send error: {e}")

        self._plugin.run_async(task())

    def _handle_clear(self, sender: Player) -> None:
        async def task():
            try:
                await self._plugin._mail_repo.clear_mail(str(sender.unique_id))

                def notify():
                    sender.send_message(self._plugin.msg("mail-clear"))
                self._plugin.server.scheduler.run_task(self._plugin, notify)
            except Exception as e:
                self._plugin.logger.error(f"Mail clear error: {e}")

        self._plugin.run_async(task())


class ListCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        try:
            players = list(self._plugin.server.online_players)
        except Exception as e:
            self._plugin.logger.error(f"Error getting online players: {e}")
            sender.send_message(self._plugin.msg("error-generic"))
            return True

        if not players:
            sender.send_message(self._plugin.msg("list-header", online=0, max=self._plugin.server.max_players))
            return True

        sender.send_message(
            self._plugin.msg("list-header", online=len(players), max=self._plugin.server.max_players)
        )
        names = [p.name for p in players]
        sender.send_message("§f" + ", ".join(names))
        sender.send_message(self._plugin.msg("list-footer"))
        return True


class HelpCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        page = 1
        if args:
            try:
                page = max(1, int(args[0]))
            except ValueError:
                pass

        lines = [
            ("§e/jwp <player> [target] §7- Teleport to player"),
            ("§e/tphere <player> §7- Teleport player to you"),
            ("§e/jwhome [name] §7- Teleport to home"),
            ("§e/jwsethome [name] §7- Set a home"),
            ("§e/jwdelhome <name> §7- Delete a home"),
            ("§e/jwwarp <name> §7- Teleport to warp"),
            ("§e/jwsetwarp <name> §7- Set a warp"),
            ("§e/jwspawn §7- Teleport to spawn"),
            ("§e/tpa <player> §7- Teleport request"),
            ("§e/tpaccept §7- Accept teleport"),
            ("§e/tpdeny §7- Decline teleport"),
            ("§e/jwmsg <player> <msg> §7- Private message"),
            ("§e/jwr <msg> §7- Reply to message"),
            ("§e/jwafk §7- Toggle AFK status"),
            ("§e/jwgod [player] §7- Toggle god mode"),
            ("§e/jwheal [player] §7- Heal yourself/others"),
            ("§e/jwgm <mode> [p] §7- Set game mode"),
            ("§e/jwfly [player] §7- Toggle flight"),
            ("§e/jwspeed <n> [fly] §7- Set speed"),
            ("§e/jwnick <name> §7- Set nickname"),
            ("§e/jwkill [player] §7- Kill yourself/others"),
            ("§e/jwhat §7- Wear item as hat"),
            ("§e/enderchest [p] §7- Open ender chest"),
            ("§e/jmail read §7- Read mail"),
            ("§e/jmail send <p> <m> §7- Send mail"),
            ("§e/jwlist §7- List online players"),
            ("§e/vanish §7- Toggle vanish"),
            ("§e/jwptime <time> §7- Set personal time"),
            ("§e/jwtop §7- Teleport to surface"),
            ("§e/jwworkbench §7- Open workbench"),
        ]

        per_page = 8
        total_pages = (len(lines) + per_page - 1) // per_page
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        end = start + per_page

        sender.send_message(
            self._plugin.msg("help-header", page=page, total=total_pages)
        )
        for line in lines[start:end]:
            sender.send_message(line)

        return True


class WorkbenchCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.msg("player-only"))
            return True

        sender.send_message(self._plugin.msg("workbench"))
        return True
