from __future__ import annotations

import asyncio
import os
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Any

from endstone.plugin import Plugin
from endstone.command import Command, CommandSender

from jwessentials.api.economy_api import EconomyAPI
from jwessentials.commands.home_commands import HomeCommandHandler, SetHomeCommandHandler, DelHomeCommandHandler
from jwessentials.commands.mail_commands import MailCommandHandler, ListCommandHandler, HelpCommandHandler, WorkbenchCommandHandler
from jwessentials.commands.social_commands import MsgCommandHandler, ReplyCommandHandler, SocialSpyCommandHandler, AfkCommandHandler
from jwessentials.commands.spawn_commands import SpawnCommandHandler, SetSpawnCommandHandler
from jwessentials.commands.teleport_commands import TeleportCommandHandler
from jwessentials.commands.teleport_commands_v2 import (
    TPACommandHandler, TPAHereCommandHandler, TPAcceptHandler, TPAcDenyHandler,
    TPAcCancelHandler, TPOHereCommandHandler,
)
from jwessentials.commands.time_commands import TimeCommandHandler, PTimeCommandHandler, WeatherCommandHandler, TopCommandHandler, JumpCommandHandler
from jwessentials.commands.utility_commands import (
    GodCommandHandler, HealCommandHandler, GameModeCommandHandler,
    FlyCommandHandler, SpeedCommandHandler, NickCommandHandler, VanishCommandHandler,
    KillCommandHandler, ClearCommandHandler, HatCommandHandler, RepairCommandHandler,
    InvSeeCommandHandler, EnderChestCommandHandler,
)
from jwessentials.commands.warp_commands import WarpCommandHandler, SetWarpCommandHandler, DelWarpCommandHandler
from jwessentials.commands.moderation_commands import (
    RTPCommandHandler, KickCommandHandler, BanCommandHandler,
    MuteCommandHandler, UnmuteCommandHandler, JailCommandHandler, UnjailCommandHandler,
)
from jwessentials.commands.tpa_settings_command import TPASettingsCommandHandler
from jwessentials.commands.reload_command import ReloadCommandHandler
from jwessentials.handlers.scoreboard_handler import ScoreboardHandler
from jwessentials.handlers.bossbar_handler import BossbarHandler
from jwessentials.database.database_manager import DatabaseManager
from jwessentials.database.repositories.home_repository import HomeRepository
from jwessentials.database.repositories.mail_repository import (
    MailRepository, PlayerDataRepository, SocialSpyRepository,
)
from jwessentials.database.repositories.profile_repository import ProfileRepository
from jwessentials.database.repositories.tpa_repository import TPARequestRepository
from jwessentials.database.repositories.warp_repository import SpawnRepository, WarpRepository
from jwessentials.database.schema import SchemaManager
from jwessentials.listeners.player_listener import PlayerListener
from jwessentials.util.config_loader import ConfigLoader
from jwessentials.util.message_formatter import MessageFormatter
from jwessentials.util.messages_loader import MessagesLoader

if TYPE_CHECKING:
    from concurrent.futures import Future


class JWEssentials(Plugin):

    api_version = "0.11"
    prefix = "§6§l[JWEssentials]§r"
    version = "1.0.0"
    description = "JWEssentials - Essential commands plugin for EndstoneMC, inspired by EssentialsX."
    authors = ["JWDev"]
    depend = ["jweconomy"]

    commands = {
        "jwp": {
            "description": "Teleport to a player or coordinates",
            "usages": [
                "/jwp <player: string>",
                "/jwp <player: string> <target: string>",
                "/jwp <x: float> <y: float> <z: float> [world: string]",
            ],
            "aliases": ["tp", "teleport"],
        },
        "tphere": {
            "description": "Teleport a player to your location",
            "usages": ["/tphere <player: string>"],
            "permissions": ["jwessentials.tphere"],
        },
        "home": {
            "description": "Teleport to your home",
            "usages": ["/home [name: string]"],
            "aliases": ["jwhome", "homes"],
        },
        "sethome": {
            "description": "Set a home location",
            "usages": ["/sethome [name: string]"],
            "aliases": ["jwsethome"],
        },
        "delhome": {
            "description": "Delete a home location",
            "usages": ["/delhome <name: string>"],
            "aliases": ["jwdelhome"],
        },
        "warp": {
            "description": "Teleport to a warp point",
            "usages": ["/warp [name: string]"],
            "permissions": ["jwessentials.warp.use"],
            "aliases": ["jwwarp"],
        },
        "setwarp": {
            "description": "Set a warp point",
            "usages": ["/setwarp <name: string>"],
            "permissions": ["jwessentials.warp.admin"],
            "aliases": ["jwsetwarp"],
        },
        "delwarp": {
            "description": "Delete a warp point",
            "usages": ["/delwarp <name: string>"],
            "permissions": ["jwessentials.warp.admin"],
            "aliases": ["jwdelwarp"],
        },
        "spawn": {
            "description": "Teleport to the server spawn",
            "usages": ["/spawn"],
            "aliases": ["jwspawn"],
        },
        "setspawn": {
            "description": "Set the server spawn point",
            "usages": ["/setspawn"],
            "permissions": ["jwessentials.spawn.admin"],
            "aliases": ["jwsetspawn"],
        },
        "tpa": {
            "description": "Request teleport to a player",
            "usages": ["/tpa <player: string>"],
        },
        "tpahere": {
            "description": "Request player to teleport to you",
            "usages": ["/tpahere <player: string>"],
        },
        "tpaccept": {
            "description": "Accept teleport request",
            "usages": ["/tpaccept"],
            "aliases": ["tpaaccept", "tpac"],
        },
        "tpdeny": {
            "description": "Decline teleport request",
            "usages": ["/tpdeny"],
            "aliases": ["tpadeny", "tpad"],
        },
        "tpcancel": {
            "description": "Cancel your teleport request",
            "usages": ["/tpcancel"],
        },
        "jwmsg": {
            "description": "Send a private message",
            "usages": ["/jwmsg <player: string> <message: string>"],
            "aliases": ["msg", "message", "tell", "whisper", "dm"],
        },
        "jwr": {
            "description": "Reply to a private message",
            "usages": ["/jwr <message: string>"],
            "aliases": ["r", "reply"],
        },
        "jwsocialspy": {
            "description": "Toggle social spy",
            "usages": ["/jwsocialspy"],
            "aliases": ["socialspy", "ss"],
            "permissions": ["jwessentials.socialspy"],
        },
        "jwafk": {
            "description": "Toggle AFK status",
            "usages": ["/jwafk"],
            "aliases": ["afk"],
        },
        "jwgod": {
            "description": "Toggle god mode",
            "usages": ["/jwgod [player: string]"],
            "permissions": ["jwessentials.god"],
            "aliases": ["god"],
        },
        "jwheal": {
            "description": "Heal yourself or others",
            "usages": ["/jwheal [player: string]"],
            "aliases": ["heal"],
        },
        "jwgm": {
            "description": "Set game mode",
            "usages": ["/jwgm <mode: string> [player: string]"],
            "aliases": ["gm", "gamemode"],
            "permissions": ["jwessentials.gamemode"],
        },
        "jwfly": {
            "description": "Toggle flight",
            "usages": ["/jwfly [player: string]"],
            "permissions": ["jwessentials.fly"],
            "aliases": ["fly"],
        },
        "jwspeed": {
            "description": "Set walk or fly speed",
            "usages": ["/jwspeed <speed: float> [fly] [player: string]", "/jwspeed <speed: float> [walk] [player: string]"],
            "permissions": ["jwessentials.speed"],
            "aliases": ["speed"],
        },
        "jwnick": {
            "description": "Set your nickname",
            "usages": ["/jwnick <nickname: string> [player: string]", "/jwnick off [player: string]"],
            "aliases": ["nick"],
        },
        "vanish": {
            "description": "Toggle vanish",
            "usages": ["/vanish"],
            "permissions": ["jwessentials.vanish"],
        },
        "jwkill": {
            "description": "Kill yourself or others",
            "usages": ["/jwkill [player: string]"],
            "permissions": ["jwessentials.kill"],
            "aliases": ["kill"],
        },
        "jwclear": {
            "description": "Clear inventory",
            "usages": ["/jwclear [player: string]"],
            "permissions": ["jwessentials.clear"],
            "aliases": ["clear"],
        },
        "jwhat": {
            "description": "Wear an item as a hat",
            "usages": ["/jwhat"],
            "aliases": ["hat"],
        },
        "jwrepair": {
            "description": "Repair items",
            "usages": ["/jwrepair [hand]", "/jwrepair all"],
            "permissions": ["jwessentials.repair"],
            "aliases": ["repair"],
        },
        "invsee": {
            "description": "View a player's inventory",
            "usages": ["/invsee <player: string>"],
            "permissions": ["jwessentials.invsee"],
        },
        "enderchest": {
            "description": "Open ender chest",
            "usages": ["/enderchest [player: string]"],
        },
        "jwwtime": {
            "description": "Set world time",
            "usages": ["/jwwtime set <time: string>", "/jwwtime add <ticks: int>"],
            "permissions": ["jwessentials.time"],
            "aliases": ["jwwt"],
        },
        "jwptime": {
            "description": "Set personal time",
            "usages": [
                "/jwptime <time: string> [player: string]",
                "/jwptime reset [player: string]",
                "/jwptime get [player: string]",
            ],
            "aliases": ["ptime"],
        },
        "jwweather": {
            "description": "Set weather",
            "usages": ["/jwweather <sun|rain|thunder|clear>"],
            "permissions": ["jwessentials.weather"],
            "aliases": ["weather"],
        },
        "jwtop": {
            "description": "Teleport to the surface above",
            "usages": ["/jwtop"],
            "aliases": ["top"],
        },
        "jump": {
            "description": "Teleport down one block",
            "usages": ["/jump"],
        },
        "jmail": {
            "description": "Mail system",
            "usages": ["/jmail read", "/jmail send <player: string> <message: string>", "/jmail clear"],
            "aliases": ["mail"],
        },
        "jwlist": {
            "description": "List online players",
            "usages": ["/jwlist"],
            "aliases": ["list"],
        },
        "jwhelp": {
            "description": "Show help menu",
            "usages": ["/jwhelp [page: int]"],
            "aliases": ["help"],
        },
        "jwworkbench": {
            "description": "Open workbench",
            "usages": ["/jwworkbench"],
            "aliases": ["workbench", "craft", "crafting"],
        },
        "rtp": {
            "description": "Random teleport to a random location",
            "usages": ["/rtp"],
            "aliases": ["randomtp", "wild"],
        },
        "jwkick": {
            "description": "Kick a player from the server",
            "usages": ["/jwkick <player: string> [reason: string]"],
            "permissions": ["jwessentials.kick"],
        },
        "jwban": {
            "description": "Ban a player from the server",
            "usages": ["/jwban <player: string> [reason: string]"],
            "permissions": ["jwessentials.ban"],
        },
        "jwmute": {
            "description": "Mute a player",
            "usages": ["/jwmute <player: string> [duration: int]"],
            "permissions": ["jwessentials.mute"],
        },
        "jwunmute": {
            "description": "Unmute a player",
            "usages": ["/jwunmute <player: string>"],
            "permissions": ["jwessentials.mute"],
        },
        "jwjail": {
            "description": "Jail a player",
            "usages": ["/jwjail <player: string> [reason: string]"],
            "permissions": ["jwessentials.jail"],
        },
        "jwunjail": {
            "description": "Unjail a player",
            "usages": ["/jwunjail <player: string>"],
            "permissions": ["jwessentials.jail"],
        },
        "tpasettings": {
            "description": "Open TPA settings",
            "usages": ["/tpasettings"],
            "aliases": ["tpaset"],
        },
        "jwreload": {
            "description": "Reload plugin config, messages, scoreboard, or bossbar",
            "usages": ["/jwreload [config|messages|scoreboard|bossbar|all]"],
            "permissions": ["jwessentials.reload"],
            "aliases": ["reload"],
        },
    }

    permissions = {
        "jwessentials.*": {
            "description": "All JWEssentials permissions",
            "default": "op",
            "children": {
                "jwessentials.tp": True,
                "jwessentials.tphere": True,
                "jwessentials.home": True,
                "jwessentials.sethome": True,
                "jwessentials.warp.use": True,
                "jwessentials.warp.admin": True,
                "jwessentials.spawn": True,
                "jwessentials.spawn.admin": True,
                "jwessentials.tpa": True,
                "jwessentials.tpahere": True,
                "jwessentials.tpaccept": True,
                "jwessentials.tpdeny": True,
                "jwessentials.msg": True,
                "jwessentials.reply": True,
                "jwessentials.socialspy": True,
                "jwessentials.afk": True,
                "jwessentials.god": True,
                "jwessentials.heal": True,
                "jwessentials.gamemode": True,
                "jwessentials.fly": True,
                "jwessentials.speed": True,
                "jwessentials.nick": True,
                "jwessentials.vanish": True,
                "jwessentials.kill": True,
                "jwessentials.clear": True,
                "jwessentials.hat": True,
                "jwessentials.repair": True,
                "jwessentials.invsee": True,
                "jwessentials.enderchest": True,
                "jwessentials.time": True,
                "jwessentials.ptime": True,
                "jwessentials.weather": True,
                "jwessentials.top": True,
                "jwessentials.mail": True,
                "jwessentials.list": True,
                "jwessentials.help": True,
                "jwessentials.workbench": True,
                "jwessentials.rtp": True,
                "jwessentials.kick": True,
                "jwessentials.ban": True,
                "jwessentials.mute": True,
                "jwessentials.jail": True,
                "jwessentials.reload": True,
            },
        },
        "jwessentials.tp": {"description": "Use /tp command", "default": "true"},
        "jwessentials.tphere": {"description": "Use /tphere command", "default": "op"},
        "jwessentials.home": {"description": "Use /home command", "default": "true"},
        "jwessentials.sethome": {"description": "Use /sethome command", "default": "true"},
        "jwessentials.warp.use": {"description": "Use /warp command", "default": "true"},
        "jwessentials.warp.admin": {"description": "Set/delete warps", "default": "op"},
        "jwessentials.spawn": {"description": "Use /spawn command", "default": "true"},
        "jwessentials.spawn.admin": {"description": "Set spawn point", "default": "op"},
        "jwessentials.tpa": {"description": "Use /tpa command", "default": "true"},
        "jwessentials.tpahere": {"description": "Use /tpahere command", "default": "true"},
        "jwessentials.tpaccept": {"description": "Use /tpaccept command", "default": "true"},
        "jwessentials.tpdeny": {"description": "Use /tpdeny command", "default": "true"},
        "jwessentials.msg": {"description": "Use /msg command", "default": "true"},
        "jwessentials.reply": {"description": "Use /r command", "default": "true"},
        "jwessentials.socialspy": {"description": "Use /socialspy command", "default": "op"},
        "jwessentials.afk": {"description": "Use /afk command", "default": "true"},
        "jwessentials.god": {"description": "Use /god command", "default": "op"},
        "jwessentials.god.others": {"description": "Toggle god mode for others", "default": "op"},
        "jwessentials.heal": {"description": "Use /heal command", "default": "true"},
        "jwessentials.heal.others": {"description": "Heal others", "default": "op"},
        "jwessentials.gamemode": {"description": "Change game mode", "default": "op"},
        "jwessentials.gamemode.others": {"description": "Change others game mode", "default": "op"},
        "jwessentials.fly": {"description": "Toggle flight", "default": "true"},
        "jwessentials.fly.others": {"description": "Toggle flight for others", "default": "op"},
        "jwessentials.speed": {"description": "Set speed", "default": "op"},
        "jwessentials.nick": {"description": "Set nickname", "default": "true"},
        "jwessentials.nick.others": {"description": "Set others nickname", "default": "op"},
        "jwessentials.vanish": {"description": "Toggle vanish", "default": "op"},
        "jwessentials.kill": {"description": "Kill players", "default": "op"},
        "jwessentials.clear": {"description": "Clear inventory", "default": "op"},
        "jwessentials.hat": {"description": "Use hat command", "default": "true"},
        "jwessentials.repair": {"description": "Repair items", "default": "true"},
        "jwessentials.invsee": {"description": "View player inventory", "default": "op"},
        "jwessentials.enderchest": {"description": "Open ender chest", "default": "true"},
        "jwessentials.enderchest.others": {"description": "Open others ender chest", "default": "op"},
        "jwessentials.time": {"description": "Set world time", "default": "op"},
        "jwessentials.ptime": {"description": "Set personal time", "default": "true"},
        "jwessentials.ptime.others": {"description": "Set others personal time", "default": "op"},
        "jwessentials.weather": {"description": "Set weather", "default": "op"},
        "jwessentials.top": {"description": "Use /top command", "default": "true"},
        "jwessentials.mail": {"description": "Use mail system", "default": "true"},
        "jwessentials.list": {"description": "Use /list command", "default": "true"},
        "jwessentials.help": {"description": "Use /help command", "default": "true"},
        "jwessentials.workbench": {"description": "Use /workbench command", "default": "true"},
        "jwessentials.rtp": {"description": "Use /rtp command", "default": "true"},
        "jwessentials.kick": {"description": "Kick players", "default": "op"},
        "jwessentials.ban": {"description": "Ban players", "default": "op"},
        "jwessentials.mute": {"description": "Mute players", "default": "op"},
        "jwessentials.jail": {"description": "Jail players", "default": "op"},
        "jwessentials.afk.notify": {"description": "Get AFK notifications", "default": "op"},
        "jwessentials.reload": {"description": "Reload plugin components", "default": "op"},
    }

    _instance: JWEssentials | None = None

    @classmethod
    def get_instance(cls) -> JWEssentials:
        if cls._instance is None:
            raise RuntimeError("JWEssentials is not loaded")
        return cls._instance

    def _load_resource_configs(self) -> tuple[dict, dict]:
        import yaml
        scoreboard_defaults = {}
        bossbar_defaults = {}
        resources_dir = Path(__file__).parent / "resources"
        sb_path = resources_dir / "scoreboard.yml"
        if sb_path.exists():
            with sb_path.open("r", encoding="utf-8") as f:
                scoreboard_defaults = yaml.safe_load(f) or {}
        bb_path = resources_dir / "bossbar.yml"
        if bb_path.exists():
            with bb_path.open("r", encoding="utf-8") as f:
                bossbar_defaults = yaml.safe_load(f) or {}
        return scoreboard_defaults, bossbar_defaults

    def on_load(self) -> None:
        JWEssentials._instance = self
        self._async_loop: asyncio.AbstractEventLoop | None = None
        self._async_thread: threading.Thread | None = None

        self._config_loader = ConfigLoader(self.data_folder, self.logger)
        scoreboard_defaults, bossbar_defaults = self._load_resource_configs()
        self._config_loader.load_all(scoreboard_defaults, bossbar_defaults)

        messages_loader = MessagesLoader(self.data_folder, self.logger)
        defaults_path = Path(__file__).parent / "resources" / "messages.yml"
        _defaults = {}
        if defaults_path.exists():
            import yaml
            with defaults_path.open("r", encoding="utf-8") as f:
                _defaults = yaml.safe_load(f) or {}
        self._messages = messages_loader.load(_defaults)
        self._message_formatter = MessageFormatter(self._messages)

        db_path = os.path.join(self.data_folder, self._config_loader.general_config.get("database_filename", "jwessentials.db"))
        self._db_manager = DatabaseManager(db_path, self.logger)

        self._start_async_loop()

        self._afk_players: dict[str, bool] = {}
        self._socialspy_cache: dict[str, bool] = {}
        self._last_replier: dict[str, str] = {}
        self._max_cache_size = self._config_loader.performance_config.get("cache-max-size", 500)

    def on_enable(self) -> None:
        future = self.run_async(self._initialize_database())
        try:
            future.result(timeout=10.0)
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            self.server.plugin_manager.disable_plugin(self)
            return

        self._profile_repo = ProfileRepository(self._db_manager)
        self._home_repo = HomeRepository(self._db_manager)
        self._warp_repo = WarpRepository(self._db_manager)
        self._spawn_repo = SpawnRepository(self._db_manager)
        self._tpa_repo = TPARequestRepository(self._db_manager)
        self._mail_repo = MailRepository(self._db_manager)
        self._player_data_repo = PlayerDataRepository(self._db_manager)
        self._socialspy_repo = SocialSpyRepository(self._db_manager)

        self._economy_api = EconomyAPI()
        jweconomy_plugin = self.server.plugin_manager.get_plugin("jweconomy")
        if jweconomy_plugin:
            self._economy_api.set_plugin(jweconomy_plugin)
        else:
            self.logger.warning("JWEconomy plugin not found. Economy features will be disabled.")

        self._cmd_tp = TeleportCommandHandler(self)
        self._cmd_tphere = TPOHereCommandHandler(self)
        self._cmd_home = HomeCommandHandler(self)
        self._cmd_sethome = SetHomeCommandHandler(self)
        self._cmd_delhome = DelHomeCommandHandler(self)
        self._cmd_warp = WarpCommandHandler(self)
        self._cmd_setwarp = SetWarpCommandHandler(self)
        self._cmd_delwarp = DelWarpCommandHandler(self)
        self._cmd_spawn = SpawnCommandHandler(self)
        self._cmd_setspawn = SetSpawnCommandHandler(self)
        self._cmd_tpa = TPACommandHandler(self)
        self._cmd_tpahere = TPAHereCommandHandler(self)
        self._cmd_tpaccept = TPAcceptHandler(self)
        self._cmd_tpdeny = TPAcDenyHandler(self)
        self._cmd_tpcancel = TPAcCancelHandler(self)
        self._cmd_msg = MsgCommandHandler(self)
        self._cmd_reply = ReplyCommandHandler(self)
        self._cmd_socialspy = SocialSpyCommandHandler(self)
        self._cmd_afk = AfkCommandHandler(self)
        self._cmd_god = GodCommandHandler(self)
        self._cmd_heal = HealCommandHandler(self)
        self._cmd_gm = GameModeCommandHandler(self)
        self._cmd_fly = FlyCommandHandler(self)
        self._cmd_speed = SpeedCommandHandler(self)
        self._cmd_nick = NickCommandHandler(self)
        self._cmd_vanish = VanishCommandHandler(self)
        self._cmd_kill = KillCommandHandler(self)
        self._cmd_clear = ClearCommandHandler(self)
        self._cmd_hat = HatCommandHandler(self)
        self._cmd_repair = RepairCommandHandler(self)
        self._cmd_invsee = InvSeeCommandHandler(self)
        self._cmd_enderchest = EnderChestCommandHandler(self)
        self._cmd_time = TimeCommandHandler(self)
        self._cmd_ptime = PTimeCommandHandler(self)
        self._cmd_weather = WeatherCommandHandler(self)
        self._cmd_top = TopCommandHandler(self)
        self._cmd_jump = JumpCommandHandler(self)
        self._cmd_mail = MailCommandHandler(self)
        self._cmd_list = ListCommandHandler(self)
        self._cmd_help = HelpCommandHandler(self)
        self._cmd_workbench = WorkbenchCommandHandler(self)
        self._cmd_rtp = RTPCommandHandler(self)
        self._cmd_kick = KickCommandHandler(self)
        self._cmd_ban = BanCommandHandler(self)
        self._cmd_mute = MuteCommandHandler(self)
        self._cmd_unmute = UnmuteCommandHandler(self)
        self._cmd_jail = JailCommandHandler(self)
        self._cmd_unjail = UnjailCommandHandler(self)
        self._cmd_tpasettings = TPASettingsCommandHandler(self)
        self._cmd_reload = ReloadCommandHandler(self)

        self._scoreboard_handler = ScoreboardHandler(self)
        self._bossbar_handler = BossbarHandler(self)

        self._muted_players: dict[str, bool] = {}
        self._jail_handler = self._cmd_jail

        from jwessentials.listeners.player_listener import PlayerListener
        listener = PlayerListener(self)
        listener._plugin = self
        self.register_events(listener)

        self._scoreboard_handler.load()
        self._bossbar_handler.load()

        self.server.scheduler.run_task(self, self._expire_tpa_requests_task, delay=600, period=600)

    def on_disable(self) -> None:
        for player in self.server.online_players:
            uuid = str(player.unique_id)
            self.run_async(self._profile_repo.upsert_profile(uuid, player.xuid, player.name))

        if hasattr(self, "_scoreboard_handler"):
            self._scoreboard_handler.disable()
        if hasattr(self, "_bossbar_handler"):
            self._bossbar_handler.disable()

        future = self.run_async(self._db_manager.close())
        try:
            future.result(timeout=5.0)
        except Exception as e:
            self.logger.error(f"Error closing database: {e}")

        self._stop_async_loop()

    def on_command(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        cmd_name = command.name.lower()

        handlers = {
            "jwp": self._cmd_tp,
            "tp": self._cmd_tp,
            "teleport": self._cmd_tp,
            "tphere": self._cmd_tphere,
            "jwhome": self._cmd_home,
            "home": self._cmd_home,
            "homes": self._cmd_home,
            "jwsethome": self._cmd_sethome,
            "sethome": self._cmd_sethome,
            "jwdelhome": self._cmd_delhome,
            "delhome": self._cmd_delhome,
            "jwwarp": self._cmd_warp,
            "warp": self._cmd_warp,
            "jwsetwarp": self._cmd_setwarp,
            "setwarp": self._cmd_setwarp,
            "jwdelwarp": self._cmd_delwarp,
            "delwarp": self._cmd_delwarp,
            "jwspawn": self._cmd_spawn,
            "spawn": self._cmd_spawn,
            "jwsetspawn": self._cmd_setspawn,
            "setspawn": self._cmd_setspawn,
            "tpa": self._cmd_tpa,
            "tpahere": self._cmd_tpahere,
            "tpaccept": self._cmd_tpaccept,
            "tpdeny": self._cmd_tpdeny,
            "tpcancel": self._cmd_tpcancel,
            "jwmsg": self._cmd_msg,
            "msg": self._cmd_msg,
            "message": self._cmd_msg,
            "tell": self._cmd_msg,
            "whisper": self._cmd_msg,
            "dm": self._cmd_msg,
            "jwr": self._cmd_reply,
            "r": self._cmd_reply,
            "reply": self._cmd_reply,
            "jwsocialspy": self._cmd_socialspy,
            "socialspy": self._cmd_socialspy,
            "ss": self._cmd_socialspy,
            "jwafk": self._cmd_afk,
            "afk": self._cmd_afk,
            "jwgod": self._cmd_god,
            "god": self._cmd_god,
            "jwheal": self._cmd_heal,
            "heal": self._cmd_heal,
            "jwgm": self._cmd_gm,
            "gm": self._cmd_gm,
            "gamemode": self._cmd_gm,
            "jwfly": self._cmd_fly,
            "fly": self._cmd_fly,
            "jwspeed": self._cmd_speed,
            "speed": self._cmd_speed,
            "jwnick": self._cmd_nick,
            "nick": self._cmd_nick,
            "vanish": self._cmd_vanish,
            "jwkill": self._cmd_kill,
            "kill": self._cmd_kill,
            "jwclear": self._cmd_clear,
            "clear": self._cmd_clear,
            "jwhat": self._cmd_hat,
            "jwrepair": self._cmd_repair,
            "invsee": self._cmd_invsee,
            "enderchest": self._cmd_enderchest,
            "jwwtime": self._cmd_time,
            "jwwt": self._cmd_time,
            "jwptime": self._cmd_ptime,
            "ptime": self._cmd_ptime,
            "jwweather": self._cmd_weather,
            "weather": self._cmd_weather,
            "jwtop": self._cmd_top,
            "top": self._cmd_top,
            "jump": self._cmd_jump,
            "jmail": self._cmd_mail,
            "mail": self._cmd_mail,
            "jwlist": self._cmd_list,
            "list": self._cmd_list,
            "jwhelp": self._cmd_help,
            "help": self._cmd_help,
            "jwworkbench": self._cmd_workbench,
            "workbench": self._cmd_workbench,
            "craft": self._cmd_workbench,
            "crafting": self._cmd_workbench,
            "rtp": self._cmd_rtp,
            "randomtp": self._cmd_rtp,
            "wild": self._cmd_rtp,
            "jwkick": self._cmd_kick,
            "jwban": self._cmd_ban,
            "jwmute": self._cmd_mute,
            "jwunmute": self._cmd_unmute,
            "jwjail": self._cmd_jail,
            "jwunjail": self._cmd_unjail,
            "tpasettings": self._cmd_tpasettings,
            "tpaset": self._cmd_tpasettings,
            "jwreload": self._cmd_reload,
            "reload": self._cmd_reload,
        }

        handler = handlers.get(cmd_name)
        if handler:
            return handler.handle(sender, args)

        return False

    def run_async(self, coro) -> Future:
        if self._async_loop is None or not self._async_loop.is_running():
            raise RuntimeError("Async loop is not running")
        return asyncio.run_coroutine_threadsafe(coro, self._async_loop)

    def _start_async_loop(self) -> None:
        def loop_runner():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._async_loop = loop
            loop.run_forever()
            loop.close()

        self._async_thread = threading.Thread(target=loop_runner, name="JWEssentialsAsyncThread", daemon=True)
        self._async_thread.start()

    def _stop_async_loop(self) -> None:
        if self._async_loop and self._async_loop.is_running():
            self._async_loop.call_soon_threadsafe(self._async_loop.stop)
        if self._async_thread:
            self._async_thread.join(timeout=5.0)

    async def _initialize_database(self) -> None:
        await self._db_manager.connect()
        schema_manager = SchemaManager(self._db_manager, self.logger)
        await schema_manager.create_tables()

    def _expire_tpa_requests_task(self) -> None:
        self.run_async(self._tpa_repo.delete_expired_requests())

    def msg(self, key: str, **kwargs) -> str:
        return self._message_formatter.format(key, **kwargs)

    def get_home_limit(self, player) -> int:
        if player.has_permission("jwessentials.home.unlimited"):
            return 999999
        if player.has_permission("jwessentials.home.vip"):
            return self._config_loader.general_config.get("vip-home-limit", 10)
        return self._config_loader.general_config.get("default-home-limit", 3)

    def get_socialspy_enabled(self) -> list[str]:
        return [k for k, v in self._socialspy_cache.items() if v]

    def cache_socialspy(self, uuid: str, enabled: bool) -> None:
        if len(self._socialspy_cache) >= self._max_cache_size and uuid not in self._socialspy_cache:
            oldest = next(iter(self._socialspy_cache))
            del self._socialspy_cache[oldest]
        self._socialspy_cache[uuid] = enabled
