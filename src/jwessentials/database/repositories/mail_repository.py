from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from jwessentials.database.database_manager import DatabaseManager

if TYPE_CHECKING:
    pass


@dataclass(frozen=True, slots=True)
class MailRecord:
    id: int
    sender_uuid: str | None
    sender_name: str
    receiver_uuid: str
    message: str
    is_read: bool
    is_legacy: bool
    created_at: str
    expires_at: str | None


class MailRepository:

    def __init__(self, db: DatabaseManager, expire_days: int = 30) -> None:
        self._db = db
        self._expire_days = expire_days

    async def send_mail(
        self,
        receiver_uuid: str,
        message: str,
        sender_uuid: str | None = None,
        sender_name: str = "Server",
        expire_days: int | None = None,
    ) -> int:
        expires = None
        if expire_days is not None and expire_days > 0:
            expires_dt = datetime.now() + timedelta(days=expire_days)
            expires = expires_dt.strftime("%Y-%m-%d %H:%M:%S")

        cursor = await self._db.execute(
            """
            INSERT INTO mail
            (sender_uuid, sender_name, receiver_uuid, message, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (sender_uuid, sender_name, receiver_uuid, message, expires),
        )
        return cursor.lastrowid

    async def get_unread_mail(self, receiver_uuid: str) -> list[MailRecord]:
        rows = await self._db.fetchall(
            """
            SELECT id, sender_uuid, sender_name, receiver_uuid, message,
                   is_read, is_legacy, created_at, expires_at
            FROM mail
            WHERE receiver_uuid = ?
            ORDER BY created_at DESC
            """,
            (receiver_uuid,),
        )
        return self._rows_to_records(rows)

    async def mark_as_read(self, mail_id: int) -> None:
        await self._db.execute(
            "UPDATE mail SET is_read = 1 WHERE id = ?",
            (mail_id,),
        )

    async def delete_mail(self, mail_id: int) -> None:
        await self._db.execute("DELETE FROM mail WHERE id = ?", (mail_id,))

    async def clear_mail(self, receiver_uuid: str) -> None:
        await self._db.execute(
            "DELETE FROM mail WHERE receiver_uuid = ?",
            (receiver_uuid,),
        )

    async def cleanup_expired_mail(self) -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = await self._db.execute(
            "DELETE FROM mail WHERE expires_at IS NOT NULL AND expires_at <= ?",
            (now,),
        )
        return cursor.rowcount

    def _rows_to_records(self, rows: list) -> list[MailRecord]:
        result = []
        for r in rows:
            expires = r["expires_at"]
            # Check if expired
            if expires:
                expires_dt = datetime.strptime(expires, "%Y-%m-%d %H:%M:%S")
                if expires_dt < datetime.now():
                    continue
            result.append(MailRecord(
                id=r["id"],
                sender_uuid=r["sender_uuid"],
                sender_name=r["sender_name"],
                receiver_uuid=r["receiver_uuid"],
                message=r["message"],
                is_read=bool(r["is_read"]),
                is_legacy=bool(r["is_legacy"]),
                created_at=r["created_at"],
                expires_at=expires,
            ))
        return result


class PlayerDataRepository:

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def ensure_exists(self, uuid: str) -> None:
        await self._db.execute(
            """
            INSERT INTO player_data (uuid, last_updated)
            VALUES (?, datetime('now'))
            ON CONFLICT(uuid) DO NOTHING
            """,
            (uuid,),
        )

    async def get_god_mode(self, uuid: str) -> bool:
        val = await self._db.fetchval(
            "SELECT god_mode FROM player_data WHERE uuid = ?",
            (uuid,),
        )
        return bool(val)

    async def set_god_mode(self, uuid: str, enabled: bool) -> None:
        await self._db.execute(
            "UPDATE player_data SET god_mode = ?, last_updated = datetime('now') WHERE uuid = ?",
            (int(enabled), uuid),
        )

    async def get_fly_mode(self, uuid: str) -> bool:
        val = await self._db.fetchval(
            "SELECT fly_mode FROM player_data WHERE uuid = ?",
            (uuid,),
        )
        return bool(val)

    async def set_fly_mode(self, uuid: str, enabled: bool) -> None:
        await self._db.execute(
            "UPDATE player_data SET fly_mode = ?, last_updated = datetime('now') WHERE uuid = ?",
            (int(enabled), uuid),
        )

    async def get_walk_speed(self, uuid: str) -> float:
        val = await self._db.fetchval(
            "SELECT walk_speed FROM player_data WHERE uuid = ?",
            (uuid,),
        )
        return val if val is not None else 0.2

    async def set_walk_speed(self, uuid: str, speed: float) -> None:
        await self._db.execute(
            "UPDATE player_data SET walk_speed = ?, last_updated = datetime('now') WHERE uuid = ?",
            (speed, uuid),
        )

    async def get_fly_speed(self, uuid: str) -> float:
        val = await self._db.fetchval(
            "SELECT fly_speed FROM player_data WHERE uuid = ?",
            (uuid,),
        )
        return val if val is not None else 0.1

    async def set_fly_speed(self, uuid: str, speed: float) -> None:
        await self._db.execute(
            "UPDATE player_data SET fly_speed = ?, last_updated = datetime('now') WHERE uuid = ?",
            (speed, uuid),
        )


class SocialSpyRepository:

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def ensure_exists(self, uuid: str) -> None:
        await self._db.execute(
            """
            INSERT INTO socialspy (uuid, enabled)
            VALUES (?, 0)
            ON CONFLICT(uuid) DO NOTHING
            """,
            (uuid,),
        )

    async def is_enabled(self, uuid: str) -> bool:
        val = await self._db.fetchval(
            "SELECT enabled FROM socialspy WHERE uuid = ?",
            (uuid,),
        )
        return bool(val)

    async def set_enabled(self, uuid: str, enabled: bool) -> None:
        await self._db.execute(
            "UPDATE socialspy SET enabled = ? WHERE uuid = ?",
            (int(enabled), uuid),
        )

    async def get_all_enabled(self) -> list[str]:
        rows = await self._db.fetchall(
            "SELECT uuid FROM socialspy WHERE enabled = 1"
        )
        return [r["uuid"] for r in rows]
