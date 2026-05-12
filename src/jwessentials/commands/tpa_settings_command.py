from __future__ import annotations

from typing import TYPE_CHECKING

from endstone import Player
from endstone.command import CommandSender
from endstone.form import ModalForm, Toggle, Label, ActionForm

if TYPE_CHECKING:
    from jwessentials.main import JWEssentials


class TPASettingsCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin
        self._player_settings: dict[str, dict] = {}

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.msg("player-only"))
            return True

        player: Player = sender
        uuid_str = str(player.unique_id)

        if uuid_str not in self._player_settings:
            self._player_settings[uuid_str] = {
                "auto_accept": False,
                "auto_deny": False,
            }

        settings = self._player_settings[uuid_str]

        auto_accept_state = "ON" if settings["auto_accept"] else "OFF"
        auto_deny_state = "ON" if settings["auto_deny"] else "OFF"

        form = ActionForm(title="§6§lTPA Settings")
        form.add_label(f"§eAuto Accept: §a{auto_accept_state}")
        form.add_label(f"§eAuto Deny: §a{auto_deny_state}")
        form.add_label("\n§7Select an option below:")

        def on_auto_accept(p: Player):
            settings["auto_accept"] = True
            settings["auto_deny"] = False
            p.send_message("§a§lTPA Settings updated!")
            p.send_message(f"§7Auto Accept: §aON")
            p.send_message(f"§7Auto Deny: §cOFF")

        def on_auto_deny(p: Player):
            settings["auto_deny"] = True
            settings["auto_accept"] = False
            p.send_message("§a§lTPA Settings updated!")
            p.send_message(f"§7Auto Accept: §cOFF")
            p.send_message(f"§7Auto Deny: §aON")

        def on_disable(p: Player):
            settings["auto_accept"] = False
            settings["auto_deny"] = False
            p.send_message("§a§lTPA Settings updated!")
            p.send_message(f"§7Auto Accept: §cOFF")
            p.send_message(f"§7Auto Deny: §cOFF")

        form.add_button("§aAuto Accept TPA", on_click=on_auto_accept)
        form.add_button("§cAuto Deny TPA", on_click=on_auto_deny)
        form.add_button("§7Disable Auto TPA", on_click=on_disable)

        player.send_form(form)
        return True

    def get_auto_accept(self, player: Player) -> bool:
        uuid_str = str(player.unique_id)
        return self._player_settings.get(uuid_str, {}).get("auto_accept", False)

    def get_auto_deny(self, player: Player) -> bool:
        uuid_str = str(player.unique_id)
        return self._player_settings.get(uuid_str, {}).get("auto_deny", False)

    def set_auto_accept(self, player: Player, value: bool) -> None:
        uuid_str = str(player.unique_id)
        if uuid_str not in self._player_settings:
            self._player_settings[uuid_str] = {"auto_accept": False, "auto_deny": False}
        self._player_settings[uuid_str]["auto_accept"] = value

    def set_auto_deny(self, player: Player, value: bool) -> None:
        uuid_str = str(player.unique_id)
        if uuid_str not in self._player_settings:
            self._player_settings[uuid_str] = {"auto_accept": False, "auto_deny": False}
        self._player_settings[uuid_str]["auto_deny"] = value
