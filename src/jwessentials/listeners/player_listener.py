from __future__ import annotations

from typing import TYPE_CHECKING

from endstone.event import PlayerJoinEvent, PlayerQuitEvent, PlayerChatEvent, PlayerCommandEvent, PlayerMoveEvent, ServerListPingEvent, event_handler

if TYPE_CHECKING:
    from jwessentials.main import JWEssentials


class PlayerListener:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    @event_handler
    def on_player_join(self, event: PlayerJoinEvent) -> None:
        player = event.player
        uuid = str(player.unique_id)
        xuid = player.xuid
        username = player.name

        def init():
            if not hasattr(self._plugin, "_profile_repo") or not hasattr(self._plugin, "_socialspy_repo"):
                self._plugin.logger.warning(f"Repos not ready for {username}, skipping init")
                return
            try:
                self._plugin.run_async(
                    self._plugin._profile_repo.upsert_profile(uuid, xuid, username)
                )
            except Exception as e:
                self._plugin.logger.error(f"Error initializing player {username}: {e}")

            try:
                self._plugin.run_async(self._load_socialspy(uuid))
                self._plugin.run_async(self._load_vanish_state(player, uuid))
            except Exception as e:
                self._plugin.logger.error(f"Error loading states for {username}: {e}")

        self._plugin.server.scheduler.run_task(self._plugin, init)

        if hasattr(self._plugin, "_scoreboard_handler"):
            self._plugin._scoreboard_handler.on_player_join(player)
        if hasattr(self._plugin, "_bossbar_handler"):
            self._plugin._bossbar_handler.on_player_join(player)

    async def _load_vanish_state(self, player, uuid: str) -> None:
        try:
            profile = await self._plugin._profile_repo.get_profile(uuid)
            if profile and profile.is_vanished:
                if not hasattr(self._plugin, "_vanished_players"):
                    self._plugin._vanished_players = set()
                self._plugin._vanished_players.add(uuid)
                
                def apply_vanish():
                    player.is_name_tag_visible = False
                    self._plugin.server.dispatch_command(
                        self._plugin.server.command_sender,
                        f"effect \"{player.name}\" invisibility 999999 255 true"
                    )
                self._plugin.server.scheduler.run_task(self._plugin, apply_vanish)
        except Exception as e:
            self._plugin.logger.error(f"Error loading vanish state: {e}")

    async def _load_socialspy(self, uuid: str) -> None:
        try:
            enabled = await self._plugin._socialspy_repo.is_enabled(uuid)
            if enabled:
                self._plugin.cache_socialspy(uuid, True)
        except Exception as e:
            self._plugin.logger.error(f"Error loading social spy state: {e}")

    @event_handler
    def on_player_quit(self, event: PlayerQuitEvent) -> None:
        player = event.player
        uuid = str(player.unique_id)
        username = player.name.lower()

        self._plugin._afk_players.pop(username, None)
        self._plugin._socialspy_cache.pop(uuid, None)
        if hasattr(self._plugin, "_vanished_players"):
            self._plugin._vanished_players.discard(uuid)

        if hasattr(self._plugin, "_scoreboard_handler"):
            self._plugin._scoreboard_handler.on_player_quit(player)
        if hasattr(self._plugin, "_bossbar_handler"):
            self._plugin._bossbar_handler.on_player_quit(player)

        def save():
            if not hasattr(self._plugin, "_profile_repo"):
                return
            try:
                self._plugin.run_async(
                    self._plugin._profile_repo.upsert_profile(uuid, player.xuid, username)
                )
            except Exception as e:
                self._plugin.logger.error(f"Error saving player data on quit for {username}: {e}")

        self._plugin.server.scheduler.run_task(self._plugin, save)

    @event_handler
    def on_player_chat(self, event: PlayerChatEvent) -> None:
        player = event.player
        uuid_str = str(player.unique_id)

        if hasattr(self._plugin, "_muted_players") and uuid_str in self._plugin._muted_players:
            event.is_cancelled = True
            player.send_message(self._plugin.msg("player-muted"))
            return

        if hasattr(self._plugin, "_vanished_players") and uuid_str in self._plugin._vanished_players:
            event.is_cancelled = True
            player.send_message("§cYou cannot chat while vanished.")
            return

        if self._plugin._afk_players.get(player.name.lower(), False):
            self._plugin._afk_players[player.name.lower()] = False

            def un_afk():
                if not hasattr(self._plugin, "_profile_repo"):
                    return
                self._plugin.run_async(
                    self._plugin._profile_repo.update_afk(str(player.unique_id), False)
                )

            self._plugin.server.scheduler.run_task(self._plugin, un_afk)
            self._plugin.server.broadcast_message(
                self._plugin.msg("afk-removed", player=player.name)
            )

    @event_handler
    def on_player_command(self, event: PlayerCommandEvent) -> None:
        player = event.player

        if hasattr(self._plugin, "_jail_handler"):
            if self._plugin._jail_handler.is_jailed(player):
                event.is_cancelled = True
                player.send_message(self._plugin.msg("jail-no-command"))
                return

        if hasattr(self._plugin, "_muted_players"):
            uuid_str = str(player.unique_id)
            if uuid_str in self._plugin._muted_players:
                cmd = event.command.lower()
                if cmd.startswith("msg ") or cmd.startswith("tell ") or cmd.startswith("jwr ") or cmd.startswith("r "):
                    event.is_cancelled = True
                    player.send_message(self._plugin.msg("player-muted"))
                    return

    @event_handler
    def on_player_move(self, event: PlayerMoveEvent) -> None:
        player = event.player
        if hasattr(self._plugin, "_jail_handler"):
            if self._plugin._jail_handler.is_jailed(player):
                event.is_cancelled = True

    @event_handler
    def on_server_list_ping(self, event: ServerListPingEvent) -> None:
        motd_template = self._plugin._messages.get("server-motd", "")
        if not motd_template:
            return
        text = motd_template
        server = self._plugin.server
        replacements = {
            "%server_name%": server.name,
            "%server_version%": server.version,
            "%server_mc_version%": server.minecraft_version,
            "%server_online%": str(len(server.online_players)),
            "%server_max_players%": str(server.max_players),
            "%server_port%": str(server.port),
        }
        for ph, value in replacements.items():
            text = text.replace(ph, value)
        text = text.replace("&", "§")
        event.motd = text
