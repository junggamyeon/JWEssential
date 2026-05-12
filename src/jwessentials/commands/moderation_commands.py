from __future__ import annotations

import random
from typing import TYPE_CHECKING

from endstone import Player
from endstone.command import CommandSender
from endstone.level import Location

if TYPE_CHECKING:
    from jwessentials.main import JWEssentials


class RTPCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.msg("player-only"))
            return True

        player: Player = sender

        rtp_config = self._plugin._config_loader.rtp_config
        max_x = rtp_config.get("max-x", 10000)
        max_z = rtp_config.get("max-z", 10000)
        min_y = rtp_config.get("min-y", 64)
        max_y = rtp_config.get("max-y", 320)
        cooldown = rtp_config.get("cooldown-seconds", 30)
        center_x = rtp_config.get("center-x", 0)
        center_z = rtp_config.get("center-z", 0)

        uuid_str = str(player.unique_id)
        if hasattr(self._plugin, "_rtp_cooldowns"):
            if uuid_str in self._plugin._rtp_cooldowns:
                remaining = self._plugin._rtp_cooldowns[uuid_str]
                if remaining > 0:
                    player.send_message(self._plugin.msg("rtp-cooldown", seconds=remaining))
                    return True
        else:
            self._plugin._rtp_cooldowns = {}

        current_location = player.location
        level = player.level  # Actor.level, not Location.level

        # Ensure player is in the Overworld
        from endstone.level import Dimension
        if current_location.dimension.type != Dimension.OVERWORLD:
            msg = self._plugin.msg("rtp-overworld-only")
            if "Missing message" in msg:
                msg = "§cRTP can only be used in the Overworld."
            player.send_message(msg)
            return True

        use_economy = rtp_config.get("use-economy", True)
        cost = rtp_config.get("cost", 0)

        if use_economy and cost > 0:
            async def process_economy():
                has_balance = await self._plugin._economy_api.has_balance(uuid_str, cost)
                if not has_balance:
                    return False
                success = await self._plugin._economy_api.remove_balance(uuid_str, cost)
                return success

            def on_economy_done(future):
                try:
                    success = future.result()
                    if not success:
                        msg = self._plugin.msg("insufficient-balance", amount=cost)
                        if "Missing message" in msg:
                            msg = f"§cYou do not have enough money. Required: {cost}"
                        self._plugin.server.scheduler.run_task(self._plugin, lambda: player.send_message(msg))
                        return
                    
                    self._plugin.server.scheduler.run_task(
                        self._plugin, 
                        lambda: self._execute_rtp(player, current_location, rtp_config, cooldown, uuid_str)
                    )
                except Exception as e:
                    self._plugin.logger.error(f"Economy check failed: {e}")
                    self._plugin.server.scheduler.run_task(
                        self._plugin, 
                        lambda: player.send_message("§cAn economy error occurred.")
                    )

            future = self._plugin.run_async(process_economy())
            future.add_done_callback(on_economy_done)
            return True
        else:
            self._execute_rtp(player, current_location, rtp_config, cooldown, uuid_str)
            return True

    def _execute_rtp(self, player, current_location, rtp_config, cooldown, uuid_str):
        attempts = 0
        max_attempts = rtp_config.get("max-attempts", 10)
        max_x = rtp_config.get("max-x", 10000)
        max_z = rtp_config.get("max-z", 10000)
        min_y = rtp_config.get("min-y", 64)
        max_y = rtp_config.get("max-y", 320)
        center_x = rtp_config.get("center-x", 0)
        center_z = rtp_config.get("center-z", 0)

        from endstone.level import Location
        import random

        for _ in range(max_attempts):
            offset_x = random.randint(-max_x, max_x)
            offset_z = random.randint(-max_z, max_z)

            x = center_x + offset_x
            z = center_z + offset_z

            from endstone.block import Block
            safe_y = self._find_safe_y(current_location.dimension, x, z, min_y, max_y)
            if safe_y is not None:
                final_loc = Location(current_location.dimension, x, safe_y + 1, z, current_location.pitch, current_location.yaw)

                def do_teleport():
                    player.teleport(final_loc)
                    # Grant Resistance for 15 seconds to survive fall if chunk was unloaded
                    self._plugin.server.dispatch_command(self._plugin.server.command_sender, f"effect \"{player.name}\" resistance 15 255 true")
                    
                    player.send_message(self._plugin.msg("rtp-teleported", x=int(x), y=int(safe_y + 1), z=int(z)))
                    self._plugin._rtp_cooldowns[uuid_str] = cooldown

                    def reset_cooldown():
                        if uuid_str in self._plugin._rtp_cooldowns:
                            self._plugin._rtp_cooldowns[uuid_str] = 0

                    if cooldown > 0:
                        self._plugin.server.scheduler.run_task(self._plugin, reset_cooldown, delay=cooldown * 20)

                self._plugin.server.scheduler.run_task(self._plugin, do_teleport)
                return

            attempts += 1

        self._plugin.server.scheduler.run_task(self._plugin, lambda: player.send_message(self._plugin.msg("rtp-failed")))

    def _find_safe_y(self, dim, x: float, z: float, min_y: int, max_y: int) -> int | None:
        if dim is None:
            self._plugin.logger.error("RTP: dimension is None")
            return None

        ix, iz = int(x), int(z)
        try:
            y = dim.get_highest_block_y_at(ix, iz)
            block = dim.get_block_at(ix, y, iz)
            type_name = ""
            if block:
                type_name = getattr(block, "type", "")
                if hasattr(type_name, "id"):
                    type_name = type_name.id
                type_name = str(type_name).lower()

            # If chunk is unloaded, it returns max height (319) and air.
            if y == 319 and "air" in type_name:
                return 319

            if y < min_y or y >= max_y:
                return None
                
            # Basic safety check for loaded chunks
            if "lava" in type_name or "water" in type_name or "air" in type_name:
                return None
            
            return y
        except Exception as e:
            self._plugin.logger.error(f"Error finding safe y: {e}")
            pass
        return None


class KickCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not args:
            sender.send_message("§c/jwkick <player> [reason]")
            return True

        target_name = args[0]
        target = self._plugin.server.get_player(target_name)

        if target is None:
            sender.send_message(self._plugin.msg("player-not-found", player=target_name))
            return True

        if target.has_permission("jwessentials.kick.exempt"):
            sender.send_message(self._plugin.msg("kick-exempt"))
            return True

        reason = " ".join(args[1:]) if len(args) > 1 else "No reason provided"
        reason_msg = self._plugin.msg("kick-reason", reason=reason)

        def do_kick():
            target.kick(reason_msg)
            sender.send_message(self._plugin.msg("kick-sent", player=target.name))

        self._plugin.server.scheduler.run_task(self._plugin, do_kick)
        return True


class BanCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not args:
            sender.send_message("§c/ban <player> [reason]")
            return True

        target_name = args[0]
        reason = " ".join(args[1:]) if len(args) > 1 else "Banned by an administrator"

        async def task():
            try:
                ban_list = self._plugin.server.ban_list
                target = self._plugin.server.get_player(target_name)
                player_uuid = target.unique_id if target else None
                player_xuid = target.xuid if target else None
                ban_list.add_ban(target_name, player_uuid, player_xuid, reason)
                if target:
                    def do_ban():
                        target.kick(self._plugin.msg("ban-kick-message", player=target_name, reason=reason))
                    self._plugin.server.scheduler.run_task(self._plugin, do_ban)

                def notify():
                    sender.send_message(self._plugin.msg("ban-sent", player=target_name))
                self._plugin.server.scheduler.run_task(self._plugin, notify)
            except Exception as e:
                self._plugin.logger.error(f"Ban error: {e}")

        self._plugin.run_async(task())
        return True


class MuteCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not args:
            sender.send_message("§c/jwmute <player> [duration in minutes]")
            return True

        target_name = args[0]
        target = self._plugin.server.get_player(target_name)

        if target is None:
            sender.send_message(self._plugin.msg("player-not-found", player=target_name))
            return True

        duration_minutes = None
        if len(args) > 1:
            try:
                duration_minutes = int(args[1])
            except ValueError:
                sender.send_message("§cInvalid duration.")
                return True

        uuid_str = str(target.unique_id)
        self._plugin._muted_players[uuid_str] = True

        sender.send_message(self._plugin.msg("mute-sent", player=target_name))

        if duration_minutes:
            def unmute_later():
                if uuid_str in self._plugin._muted_players:
                    del self._plugin._muted_players[uuid_str]
                    if target.is_online:
                        target.send_message(self._plugin.msg("mute-expired"))

            self._plugin.server.scheduler.run_task(
                self._plugin,
                unmute_later,
                delay=duration_minutes * 60 * 20
            )

        return True

    def is_muted(self, player: Player) -> bool:
        return str(player.unique_id) in self._plugin._muted_players


class UnmuteCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not args:
            sender.send_message("§c/jwunmute <player>")
            return True

        target_name = args[0]
        target = self._plugin.server.get_player(target_name)

        if target is None:
            sender.send_message(self._plugin.msg("player-not-found", player=target_name))
            return True

        uuid_str = str(target.unique_id)
        if uuid_str in self._plugin._muted_players:
            del self._plugin._muted_players[uuid_str]
            sender.send_message(self._plugin.msg("unmute-sent", player=target_name))
        else:
            sender.send_message(self._plugin.msg("player-not-muted", player=target_name))

        return True


class JailCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin
        self._jailed_players: dict[str, dict] = {}

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not args:
            sender.send_message("§c/jwjail <player> [reason]")
            return True

        target_name = args[0]
        target = self._plugin.server.get_player(target_name)

        if target is None:
            sender.send_message(self._plugin.msg("player-not-found", player=target_name))
            return True

        reason = " ".join(args[1:]) if len(args) > 1 else "Jailed by an administrator"
        uuid_str = str(target.unique_id)

        original_location = {
            "x": target.location.x,
            "y": target.location.y,
            "z": target.location.z,
            "dimension": str(target.location.dimension),
            "pitch": target.location.pitch,
            "yaw": target.location.yaw,
        }
        self._jailed_players[uuid_str] = original_location

        jail_config = self._plugin._config_loader.jail_config
        jail_x = jail_config.get("x", 0)
        jail_y = jail_config.get("y", 100)
        jail_z = jail_config.get("z", 0)

        from endstone.level import Location
        dim = target.location.dimension

        jail_location = Location(dim, jail_x, jail_y, jail_z, 0, 0)

        def do_jail():
            target.teleport(jail_location)
            target.send_message(self._plugin.msg("jail-message", reason=reason))
            sender.send_message(self._plugin.msg("jail-sent", player=target_name))

        self._plugin.server.scheduler.run_task(self._plugin, do_jail)
        return True

    def is_jailed(self, player: Player) -> bool:
        return str(player.unique_id) in self._jailed_players


class UnjailCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not args:
            sender.send_message("§c/jwunjail <player>")
            return True

        target_name = args[0]
        target = self._plugin.server.get_player(target_name)

        if target is None:
            sender.send_message(self._plugin.msg("player-not-found", player=target_name))
            return True

        uuid_str = str(target.unique_id)
        if uuid_str not in self._plugin._jail_handler._jailed_players:
            sender.send_message(self._plugin.msg("player-not-jailed", player=target_name))
            return True

        original = self._plugin._jail_handler._jailed_players[uuid_str]
        del self._plugin._jail_handler._jailed_players[uuid_str]

        from endstone.level import Location
        dim = target.location.dimension

        original_location = Location(
            dim,
            original["x"],
            original["y"],
            original["z"],
            original["pitch"],
            original["yaw"],
        )

        def do_unjail():
            target.teleport(original_location)
            target.send_message(self._plugin.msg("unjail-message"))
            sender.send_message(self._plugin.msg("unjail-sent", player=target_name))

        self._plugin.server.scheduler.run_task(self._plugin, do_unjail)
        return True
