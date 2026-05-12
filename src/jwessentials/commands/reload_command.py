from __future__ import annotations

import yaml
from pathlib import Path
from typing import TYPE_CHECKING

from endstone import Player
from endstone.command import CommandSender

if TYPE_CHECKING:
    from jwessentials.main import JWEssentials


class ReloadCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        targets = args[0].lower().split(",") if args else []

        reload_all = len(targets) == 0 or "all" in targets
        reloaded = []

        if reload_all or "config" in targets:
            self._reload_config()
            reloaded.append("config")

        if reload_all or "messages" in targets:
            self._reload_messages()
            reloaded.append("messages")

        if reload_all or "scoreboard" in targets:
            self._reload_scoreboard()
            reloaded.append("scoreboard")

        if reload_all or "bossbar" in targets:
            self._reload_bossbar()
            reloaded.append("bossbar")

        if not reloaded:
            sender.send_message("§cUsage: /jwreload [config|messages|scoreboard|bossbar|all]")
            return True

        sender.send_message(self._plugin.msg("reload-success", items=", ".join(reloaded)))
        return True

    def _reload_config(self) -> None:
        try:
            self._plugin._config_loader.reload()
            self._plugin.logger.info("Config reloaded.")
        except Exception as e:
            self._plugin.logger.error(f"Failed to reload config: {e}")

    def _reload_messages(self) -> None:
        try:
            messages_path = self._plugin.data_folder / "messages.yml"
            resource_path = Path(__file__).parent.parent / "resources" / "messages.yml"

            defaults = {}
            if resource_path.exists():
                with resource_path.open("r", encoding="utf-8") as f:
                    defaults = yaml.safe_load(f) or {}

            from jwessentials.util.messages_loader import MessagesLoader
            loader = MessagesLoader(self._plugin.data_folder, self._plugin.logger)
            self._plugin._messages = loader.load(defaults)
            self._plugin._message_formatter.reload(self._plugin._messages)
            self._plugin.logger.info("Messages reloaded.")
        except Exception as e:
            self._plugin.logger.error(f"Failed to reload messages: {e}")

    def _reload_scoreboard(self) -> None:
        try:
            if hasattr(self._plugin, "_scoreboard_handler"):
                self._plugin._scoreboard_handler.disable()
                self._plugin._scoreboard_handler.load()
            self._plugin.logger.info("Scoreboard reloaded.")
        except Exception as e:
            self._plugin.logger.error(f"Failed to reload scoreboard: {e}")

    def _reload_bossbar(self) -> None:
        try:
            if hasattr(self._plugin, "_bossbar_handler"):
                self._plugin._bossbar_handler.disable()
                self._plugin._bossbar_handler.load()
            self._plugin.logger.info("Bossbar reloaded.")
        except Exception as e:
            self._plugin.logger.error(f"Failed to reload bossbar: {e}")
