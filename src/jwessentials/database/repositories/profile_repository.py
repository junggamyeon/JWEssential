from __future__ import annotations

from dataclasses import dataclass

from jwessentials.database.database_manager import DatabaseManager


@dataclass(frozen=True, slots=True)
class PlayerProfile:
    uuid: str
    xuid: str
    username: str
    nickname: str | None
    first_seen: str
    last_seen: str
    is_afk: bool
    is_vanished: bool
    is_god_mode: bool
    is_fly_mode: bool
    personal_time: int | None


class ProfileRepository:

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def upsert_profile(self, uuid: str, xuid: str, username: str) -> None:
        await self._db.execute(
            """
            INSERT INTO player_profiles (uuid, xuid, username, first_seen, last_seen)
            VALUES (?, ?, ?, datetime('now'), datetime('now'))
            ON CONFLICT(uuid) DO UPDATE SET
                username = excluded.username,
                last_seen = datetime('now')
            """,
            (uuid, xuid, username),
        )

    async def get_profile(self, uuid: str) -> PlayerProfile | None:
        row = await self._db.fetchone(
            """
            SELECT uuid, xuid, username, nickname, first_seen, last_seen,
                   is_afk, is_vanished, is_god_mode, is_fly_mode, personal_time
            FROM player_profiles WHERE uuid = ?
            """,
            (uuid,),
        )
        if row is None:
            return None
        return PlayerProfile(
            uuid=row["uuid"],
            xuid=row["xuid"],
            username=row["username"],
            nickname=row["nickname"],
            first_seen=row["first_seen"],
            last_seen=row["last_seen"],
            is_afk=bool(row["is_afk"]),
            is_vanished=bool(row["is_vanished"]),
            is_god_mode=bool(row["is_god_mode"]),
            is_fly_mode=bool(row["is_fly_mode"]),
            personal_time=row["personal_time"],
        )

    async def get_uuid_by_name(self, username: str) -> str | None:
        return await self._db.fetchval(
            "SELECT uuid FROM player_profiles WHERE username = ? COLLATE NOCASE",
            (username,),
        )

    async def update_nickname(self, uuid: str, nickname: str | None) -> None:
        await self._db.execute(
            "UPDATE player_profiles SET nickname = ? WHERE uuid = ?",
            (nickname, uuid),
        )

    async def update_afk(self, uuid: str, is_afk: bool) -> None:
        await self._db.execute(
            "UPDATE player_profiles SET is_afk = ? WHERE uuid = ?",
            (int(is_afk), uuid),
        )

    async def update_vanished(self, uuid: str, is_vanished: bool) -> None:
        await self._db.execute(
            "UPDATE player_profiles SET is_vanished = ? WHERE uuid = ?",
            (int(is_vanished), uuid),
        )

    async def update_personal_time(self, uuid: str, time_value: int | None) -> None:
        await self._db.execute(
            "UPDATE player_profiles SET personal_time = ? WHERE uuid = ?",
            (time_value, uuid),
        )

    async def get_all_online_uuids(self) -> list[str]:
        rows = await self._db.fetchall("SELECT uuid FROM player_profiles")
        return [r["uuid"] for r in rows]
