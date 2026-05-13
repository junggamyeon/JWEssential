from __future__ import annotations

from typing import TYPE_CHECKING

from endstone import Player, GameMode
from endstone.command import CommandSender
from endstone.form import ModalForm, ActionForm, Button, Label, Toggle

if TYPE_CHECKING:
    from jwessentials.main import JWEssentials


class GodCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        target = sender
        enable_override: bool | None = None

        if args and sender.has_permission("jwessentials.god.others"):
            target = self._plugin.server.get_player(args[0])
            if target is None:
                sender.send_message(self._plugin.msg("player-not-found", player=args[0]))
                return True
            if len(args) >= 2:
                enable_override = self._parse_toggle(args[1])

        sender_name = sender.name
        target_name = target.name
        sender_is_target = sender == target

        async def task():
            try:
                if enable_override is not None:
                    enable = enable_override
                else:
                    enable = not await self._plugin.player_data_repo.get_god_mode(str(target.unique_id))
                await self._plugin.player_data_repo.set_god_mode(str(target.unique_id), enable)
                
                def sync_update():
                    if enable:
                        target.health = target.max_health
                    msg = (
                        self._plugin.msg("god-self" if sender_is_target else "god-enabled", player=target_name)
                        if enable
                        else self._plugin.msg("god-self-disable" if sender_is_target else "god-disabled", player=target_name)
                    )
                    sender.send_message(msg)

                self._plugin.server.scheduler.run_task(self._plugin, sync_update)
            except Exception as e:
                self._plugin.logger.error(f"God toggle error: {e}")

        self._plugin.run_async(task())
        return True

    @staticmethod
    def _parse_toggle(arg: str) -> bool | None:
        if arg.lower() in ("on", "enable", "1", "true"):
            return True
        if arg.lower() in ("off", "disable", "0", "false"):
            return False
        return None


class HealCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        target = sender
        if args and sender.has_permission("jwessentials.heal.others"):
            target = self._plugin.server.get_player(args[0])
            if target is None:
                sender.send_message(self._plugin.msg("player-not-found", player=args[0]))
                return True

        target.health = target.max_health

        sender.send_message(
            self._plugin.msg("heal-success") if sender == target
            else self._plugin.msg("heal-other", player=target.name)
        )
        return True


class GameModeCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not args:
            sender.send_message("§c/gm <mode> [player]")
            return True

        mode_str = args[0].lower()
        mode = self._parse_gamemode(mode_str)
        if mode is None:
            sender.send_message(self._plugin.msg("gm-invalid", mode=args[0]))
            return True

        target = sender
        if len(args) >= 2 and sender.has_permission("jwessentials.gamemode.others"):
            target = self._plugin.server.get_player(args[1])
            if target is None:
                sender.send_message(self._plugin.msg("player-not-found", player=args[1]))
                return True

        target.game_mode = mode
        sender.send_message(
            self._plugin.msg("gm-changed", player=target.name, gamemode=mode.name.lower())
            if sender != target
            else self._plugin.msg("gm-self", gamemode=mode.name.lower())
        )
        return True

    @staticmethod
    def _parse_gamemode(mode_str: str) -> GameMode | None:
        if mode_str in ("0", "survival", "s", "gms"):
            return GameMode.SURVIVAL
        if mode_str in ("1", "creative", "c", "gmc"):
            return GameMode.CREATIVE
        if mode_str in ("2", "adventure", "a", "gma"):
            return GameMode.ADVENTURE
        if mode_str in ("3", "spectator", "sp", "gmsp"):
            return GameMode.SPECTATOR
        return None


class FlyCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        target = sender
        enable = None

        if args and sender.has_permission("jwessentials.fly.others"):
            target = self._plugin.server.get_player(args[0])
            if target is None:
                sender.send_message(self._plugin.msg("player-not-found", player=args[0]))
                return True
            if len(args) >= 2:
                enable = self._parse_toggle(args[1])

        if enable is None:
            enable = not target.allow_flight

        target.allow_flight = enable
        target.is_flying = enable

        if enable:
            sender.send_message(
                self._plugin.msg("fly-self" if sender == target else "fly-enabled", player=target.name)
            )
        else:
            sender.send_message(
                self._plugin.msg("fly-self-disable" if sender == target else "fly-disabled", player=target.name)
            )
        return True

    @staticmethod
    def _parse_toggle(arg: str) -> bool | None:
        if arg.lower() in ("on", "enable", "1", "true"):
            return True
        if arg.lower() in ("off", "disable", "0", "false"):
            return False
        return None


class SpeedCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if len(args) < 1:
            sender.send_message("§c/speed <speed> [fly|walk] [player]")
            return True

        try:
            speed_val = float(args[0])
        except ValueError:
            sender.send_message("§cInvalid speed value.")
            return True

        speed_val = max(0.0, min(10.0, speed_val))
        is_fly = False
        target = sender

        if len(args) >= 2:
            if args[1].lower() in ("fly", "f"):
                is_fly = True
            elif args[1].lower() in ("walk", "w"):
                is_fly = False
            else:
                target = self._plugin.server.get_player(args[1])
                if target is None:
                    sender.send_message(self._plugin.msg("player-not-found", player=args[1]))
                    return True

        if len(args) >= 3:
            target = self._plugin.server.get_player(args[2])
            if target is None:
                sender.send_message(self._plugin.msg("player-not-found", player=args[2]))
                return True

        self._apply_speed(target, speed_val, is_fly)
        type_name = "fly" if is_fly else "walk"
        sender.send_message(self._plugin.msg("speed-set", player=target.name, type=type_name, speed=speed_val))
        return True

    @staticmethod
    def _apply_speed(player: Player, speed_val: float, is_fly: bool) -> None:
        if is_fly:
            player.fly_speed = max(0.0, min(1.0, speed_val / 10.0))
        else:
            player.walk_speed = max(0.0, min(1.0, speed_val / 10.0))


class NickCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not args:
            sender.send_message("§c/nick <nickname|off> [player]")
            return True

        nickname = args[0]
        target = sender

        if len(args) >= 2 and sender.has_permission("jwessentials.nick.others"):
            target = self._plugin.server.get_player(args[1])
            if target is None:
                sender.send_message(self._plugin.msg("player-not-found", player=args[1]))
                return True

        async def task():
            try:
                if nickname.lower() == "off":
                    await self._plugin._profile_repo.update_nickname(str(target.unique_id), None)
                    def sync_update_off():
                        sender.send_message(self._plugin.msg("nick-removed"))
                    self._plugin.server.scheduler.run_task(self._plugin, sync_update_off)
                else:
                    await self._plugin._profile_repo.update_nickname(str(target.unique_id), nickname)
                    def sync_update_on():
                        sender.send_message(self._plugin.msg("nick-set", nick=nickname))
                    self._plugin.server.scheduler.run_task(self._plugin, sync_update_on)
            except Exception as e:
                self._plugin.logger.error(f"Nick error: {e}")

        self._plugin.run_async(task())
        return True


class VanishCommandHandler:

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
                enabled = not profile.is_vanished if profile else True
                await self._plugin._profile_repo.update_vanished(uuid, enabled)
                def sync_update():
                    if not hasattr(self._plugin, "_vanished_players"):
                        self._plugin._vanished_players = set()
                        
                    if enabled:
                        self._plugin._vanished_players.add(uuid)
                        sender.is_name_tag_visible = False
                        self._plugin.server.dispatch_command(
                            self._plugin.server.command_sender,
                            f"effect \"{sender.name}\" invisibility 999999 255 true"
                        )
                        sender.send_message(self._plugin.msg("vanish-enabled"))
                    else:
                        self._plugin._vanished_players.discard(uuid)
                        sender.is_name_tag_visible = True
                        self._plugin.server.dispatch_command(
                            self._plugin.server.command_sender,
                            f"effect \"{sender.name}\" clear"
                        )
                        sender.send_message(self._plugin.msg("vanish-disabled"))
                        
                self._plugin.server.scheduler.run_task(self._plugin, sync_update)
            except Exception as e:
                self._plugin.logger.error(f"Vanish error: {e}")

        self._plugin.run_async(task())
        return True


class KillCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not args:
            if not isinstance(sender, Player):
                sender.send_message("§c/kill <player>")
                return True
            target = sender
        else:
            target = self._plugin.server.get_player(args[0])
            if target is None:
                sender.send_message(self._plugin.msg("player-not-found", player=args[0]))
                return True

        target.health = 0
        sender.send_message(
            self._plugin.msg("suicide") if sender == target
            else f"§aKilled {target.name}."
        )
        return True


class ClearCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        target = sender
        if args and sender.has_permission("jwessentials.clear.others"):
            target = self._plugin.server.get_player(args[0])
            if target is None:
                sender.send_message(self._plugin.msg("player-not-found", player=args[0]))
                return True

        inv = target.inventory
        count = 0
        for slot in range(inv.size):
            item = inv.get_item(slot)
            if item is not None:
                count += item.amount
                inv.set_item(slot, None)

        sender.send_message(self._plugin.msg("clear-success", player=target.name, count=count))
        return True


class HatCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.msg("player-only"))
            return True

        player: Player = sender
        item = player.inventory.item_in_main_hand

        if item is None:
            sender.send_message(self._plugin.msg("hat-fail"))
            return True

        current_hat = player.inventory.helmet
        player.inventory.helmet = item
        player.inventory.item_in_main_hand = current_hat

        sender.send_message(self._plugin.msg("hat-success", item=item.type.id.split(":")[-1]))
        return True


class RepairCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message("§c/repair [hand|all]")
            return True

        player: Player = sender
        mode = args[0].lower() if args else "hand"

        if mode == "hand":
            item = player.inventory.item_in_main_hand
            if item is None:
                sender.send_message("§cYou are not holding an item.")
                return True
            if player.is_op and hasattr(item.item_meta, "damage") and item.item_meta.has_damage:
                item.item_meta.damage = 0
                player.inventory.item_in_main_hand = item
                sender.send_message(self._plugin.msg("repair-success"))
        elif mode == "all":
            for i in range(player.inventory.size):
                item = player.inventory.get_item(i)
                if item and player.is_op and hasattr(item, "item_meta") and item.item_meta.has_damage:
                    item.item_meta.damage = 0
                    player.inventory.set_item(i, item)
            sender.send_message(self._plugin.msg("repair-all"))
        else:
            sender.send_message(self._plugin.msg("repair-usage"))
        return True


class InvSeeCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message("§c/invsee <player>")
            return True

        if not args:
            sender.send_message(self._plugin.msg("invsee-usage"))
            return True

        target = self._plugin.server.get_player(args[0])
        if target is None:
            sender.send_message(self._plugin.msg("player-not-found", player=args[0]))
            return True

        player: Player = sender
        self._show_inventory_form(player, target)
        return True

    def _show_inventory_form(self, viewer: Player, target: Player) -> None:
        try:
            from endstone_inventoryui import Menu, MenuType
            from endstone.inventory import ItemStack
        except ImportError:
            viewer.send_message("§cInventoryUI plugin is not installed!")
            return

        target_inv = target.inventory
        menu = Menu(MenuType.DOUBLE_CHEST, f"{target.name}'s Inventory")
        ui_inv = menu.inventory
        pane = ItemStack("minecraft:black_stained_glass_pane", 1)

        for i in range(27):
            item = target_inv.get_item(i + 9)
            if item: ui_inv.set_item(i, item)
        for i in range(27, 36):
            ui_inv.set_item(i, pane)
        if target_inv.helmet: ui_inv.set_item(36, target_inv.helmet)
        if target_inv.chestplate: ui_inv.set_item(37, target_inv.chestplate)
        if target_inv.leggings: ui_inv.set_item(38, target_inv.leggings)
        if target_inv.boots: ui_inv.set_item(39, target_inv.boots)
        if getattr(target_inv, "item_in_off_hand", None): ui_inv.set_item(40, target_inv.item_in_off_hand)
        for i in range(41, 45):
            ui_inv.set_item(i, pane)
        for i in range(9):
            item = target_inv.get_item(i)
            if item: ui_inv.set_item(45 + i, item)

        taken_items = []
        given_items = []

        def on_click(p: Player, slot: int, item, inv):
            """OP clicks item in the chest UI → queue take from target"""
            if not p.is_op: return
            if item is None or (hasattr(item, "type") and "air" in item.type.id.lower()): return
            if 27 <= slot <= 35 or 41 <= slot <= 44: return

            armor_map = {36: "helmet", 37: "chestplate", 38: "leggings", 39: "boots", 40: "offhand"}
            source_slot = None
            if 0 <= slot <= 26: source_slot = slot + 9
            elif 45 <= slot <= 53: source_slot = slot - 45

            taken_items.append({
                "item": item,
                "source_slot": source_slot,
                "armor_type": armor_map.get(slot),
            })

        def on_place(p: Player, slot: int, item, inv):
            """OP clicks item in own inventory → queue give to target"""
            if not p.is_op: return
            if item is None or (hasattr(item, "type") and "air" in item.type.id.lower()): return
            given_items.append({"item": item, "player_slot": slot})

        def on_close(p: Player):
            """Deliver all pending items when menu closes"""
            if not taken_items and not given_items: return

            def do_transfers():
                t_inv = target.inventory
                for entry in taken_items:
                    p.inventory.add_item(entry["item"])
                    at = entry.get("armor_type")
                    ss = entry.get("source_slot")
                    if at:
                        attr = at if at != "offhand" else "item_in_off_hand"
                        setattr(t_inv, attr, None)
                    elif ss is not None:
                        t_inv.set_item(ss, None)
                if taken_items:
                    p.send_message(f"§aReceived {len(taken_items)} item(s) from {target.name}.")
                taken_items.clear()

                for entry in given_items:
                    t_inv.add_item(entry["item"])
                    if entry["player_slot"] is not None:
                        p.inventory.set_item(entry["player_slot"], None)
                if given_items:
                    p.send_message(f"§aGave {len(given_items)} item(s) to {target.name}.")
                given_items.clear()

            self._plugin.server.scheduler.run_task(self._plugin, do_transfers)

        menu.set_listener(on_click)
        menu.set_place_listener(on_place)
        menu.set_close_listener(on_close)
        menu.send_to(viewer)


class EnderChestCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message("§c/enderchest [player]")
            return True

        target: Player = sender
        if args and sender.has_permission("jwessentials.enderchest.others"):
            target = self._plugin.server.get_player(args[0])
            if target is None:
                sender.send_message(self._plugin.msg("player-not-found", player=args[0]))
                return True

        player: Player = sender
        try:
            from endstone_inventoryui import Menu, MenuType
        except ImportError:
            sender.send_message("§cInventoryUI plugin is not installed!")
            return

        menu = Menu(MenuType.CHEST, f"{target.name}'s Ender Chest")

        for slot in range(min(target.ender_chest.size, menu.inventory.size)):
            item = target.ender_chest.get_item(slot)
            if item:
                menu.inventory.set_item(slot, item)

        pending_ec_transfer = {}

        def on_click(p: Player, slot: int, item, inv):
            if not p.is_op:
                return
            if item is None or (hasattr(item, "type") and "air" in item.type.id.lower()):
                return

            pending_ec_transfer["item"] = item
            pending_ec_transfer["slot"] = slot
            menu.close(p)

        def on_close(p: Player):
            if not pending_ec_transfer:
                return
            item = pending_ec_transfer.pop("item", None)
            ec_slot = pending_ec_transfer.pop("slot", None)
            pending_ec_transfer.clear()
            if item is None:
                return

            def do_transfer():
                p.inventory.add_item(item)
                target.ender_chest.set_item(ec_slot, None)
                p.send_message(f"§aYou took an item from {target.name}'s ender chest.")

            self._plugin.server.scheduler.run_task(self._plugin, do_transfer)

        menu.set_listener(on_click)
        menu.set_close_listener(on_close)
        menu.send_to(player)
        return True


class EnchantCommandHandler:

    def __init__(self, plugin: JWEssentials) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if len(args) < 3:
            sender.send_message("§c/jwenchant <player> <enchantmentName> <level>")
            return True

        target_name = args[0]
        enchant_name = args[1].lower()
        
        try:
            level = int(args[2])
        except ValueError:
            sender.send_message("§cLevel must be an integer.")
            return True

        target = self._plugin.server.get_player(target_name)
        if target is None:
            sender.send_message(self._plugin.msg("player-not-found", player=target_name))
            return True

        item = target.inventory.item_in_main_hand
        if item is None or (hasattr(item, "type") and "air" in item.type.id.lower()):
            sender.send_message("§cPlayer is not holding any item.")
            return True

        if hasattr(item, "item_meta"):
            meta = item.item_meta
            success = meta.add_enchant(enchant_name, level, force=True)
            if success:
                item.set_item_meta(meta)
                target.inventory.item_in_main_hand = item
                sender.send_message(f"§aApplied enchantment {enchant_name} level {level} to {target.name}'s item.")
            else:
                sender.send_message(f"§cFailed to apply enchantment {enchant_name}. Invalid enchantment name?")
        else:
            sender.send_message("§cThis item cannot be enchanted.")
        return True

