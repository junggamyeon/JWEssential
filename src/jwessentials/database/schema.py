from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone import Logger
    from jwessentials.database.database_manager import DatabaseManager


class SchemaManager:

    def __init__(self, db: DatabaseManager, logger: Logger) -> None:
        self._db = db
        self._logger = logger

    async def create_tables(self) -> None:
        await self._create_player_profiles_table()
        await self._create_homes_table()
        await self._create_warps_table()
        await self._create_spawn_table()
        await self._create_tpa_requests_table()
        await self._create_mail_table()
        await self._create_player_data_table()
        await self._create_socialspy_table()

    async def _create_player_profiles_table(self) -> None:
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS player_profiles (
                uuid        TEXT PRIMARY KEY,
                xuid        TEXT UNIQUE,
                username    TEXT NOT NULL,
                nickname    TEXT,
                first_seen  TEXT NOT NULL DEFAULT (datetime('now')),
                last_seen   TEXT NOT NULL DEFAULT (datetime('now')),
                is_afk      INTEGER NOT NULL DEFAULT 0,
                is_vanished INTEGER NOT NULL DEFAULT 0,
                is_god_mode INTEGER NOT NULL DEFAULT 0,
                is_fly_mode INTEGER NOT NULL DEFAULT 0,
                personal_time INTEGER
            );

            CREATE INDEX IF NOT EXISTS idx_profiles_username
                ON player_profiles (username COLLATE NOCASE);

            CREATE INDEX IF NOT EXISTS idx_profiles_xuid
                ON player_profiles (xuid);
        """)

    async def _create_homes_table(self) -> None:
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS homes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                uuid        TEXT NOT NULL,
                name        TEXT NOT NULL DEFAULT 'home',
                world       TEXT NOT NULL,
                x           REAL NOT NULL,
                y           REAL NOT NULL,
                z           REAL NOT NULL,
                pitch       REAL NOT NULL DEFAULT 0,
                yaw         REAL NOT NULL DEFAULT 0,
                created_at  TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(uuid, name),
                FOREIGN KEY (uuid) REFERENCES player_profiles(uuid) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_homes_uuid
                ON homes (uuid);
        """)

    async def _create_warps_table(self) -> None:
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS warps (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT UNIQUE NOT NULL,
                world       TEXT NOT NULL,
                x           REAL NOT NULL,
                y           REAL NOT NULL,
                z           REAL NOT NULL,
                pitch       REAL NOT NULL DEFAULT 0,
                yaw         REAL NOT NULL DEFAULT 0,
                category    TEXT DEFAULT 'general',
                created_by  TEXT,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_warps_name
                ON warps (name COLLATE NOCASE);
        """)

    async def _create_spawn_table(self) -> None:
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS spawn (
                id          INTEGER PRIMARY KEY,
                world       TEXT NOT NULL,
                x           REAL NOT NULL,
                y           REAL NOT NULL,
                z           REAL NOT NULL,
                pitch       REAL NOT NULL DEFAULT 0,
                yaw         REAL NOT NULL DEFAULT 0
            );
        """)

    async def _create_tpa_requests_table(self) -> None:
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS tpa_requests (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_uuid     TEXT NOT NULL,
                sender_name     TEXT NOT NULL,
                receiver_uuid   TEXT NOT NULL,
                receiver_name   TEXT NOT NULL,
                world           TEXT,
                x               REAL,
                y               REAL,
                z               REAL,
                pitch           REAL,
                yaw             REAL,
                created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                expires_at      TEXT NOT NULL,
                FOREIGN KEY (sender_uuid) REFERENCES player_profiles(uuid) ON DELETE CASCADE,
                FOREIGN KEY (receiver_uuid) REFERENCES player_profiles(uuid) ON DELETE CASCADE
            );
        """)

    async def _create_mail_table(self) -> None:
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS mail (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_uuid     TEXT,
                sender_name     TEXT NOT NULL DEFAULT 'Server',
                receiver_uuid   TEXT NOT NULL,
                message         TEXT NOT NULL,
                is_read         INTEGER NOT NULL DEFAULT 0,
                is_legacy      INTEGER NOT NULL DEFAULT 0,
                created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                expires_at      TEXT,
                FOREIGN KEY (receiver_uuid) REFERENCES player_profiles(uuid) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_mail_receiver
                ON mail (receiver_uuid, is_read);
        """)

    async def _create_player_data_table(self) -> None:
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS player_data (
                uuid        TEXT PRIMARY KEY,
                god_mode    INTEGER NOT NULL DEFAULT 0,
                fly_mode    INTEGER NOT NULL DEFAULT 0,
                walk_speed  REAL DEFAULT 0.2,
                fly_speed   REAL DEFAULT 0.1,
                walk_speed_override REAL,
                fly_speed_override REAL,
                last_updated TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (uuid) REFERENCES player_profiles(uuid) ON DELETE CASCADE
            );
        """)

    async def _create_socialspy_table(self) -> None:
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS socialspy (
                uuid        TEXT PRIMARY KEY,
                enabled     INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (uuid) REFERENCES player_profiles(uuid) ON DELETE CASCADE
            );
        """)
