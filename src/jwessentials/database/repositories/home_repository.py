from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from jwessentials.database.database_manager import DatabaseManager

if TYPE_CHECKING:
    from endstone.level import Location


@dataclass(frozen=True, slots=True)
class HomeData:
    uuid: str
    name: str
    world: str
    x: float
    y: float
    z: float
    pitch: float
    yaw: float


class HomeRepository:

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def set_home(self, uuid: str, name: str, location: Location) -> None:
        await self._db.execute(
            """
            INSERT INTO homes (uuid, name, world, x, y, z, pitch, yaw)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(uuid, name) DO UPDATE SET
                world = excluded.world,
                x = excluded.x,
                y = excluded.y,
                z = excluded.z,
                pitch = excluded.pitch,
                yaw = excluded.yaw
            """,
            (uuid, name, location.dimension.name, location.x, location.y, location.z,
             location.pitch, location.yaw),
        )

    async def get_home(self, uuid: str, name: str) -> HomeData | None:
        row = await self._db.fetchone(
            """
            SELECT uuid, name, world, x, y, z, pitch, yaw
            FROM homes WHERE uuid = ? AND name = ?
            """,
            (uuid, name),
        )
        if row is None:
            return None
        return HomeData(
            uuid=row["uuid"],
            name=row["name"],
            world=row["world"],
            x=row["x"],
            y=row["y"],
            z=row["z"],
            pitch=row["pitch"],
            yaw=row["yaw"],
        )

    async def get_homes(self, uuid: str) -> list[HomeData]:
        rows = await self._db.fetchall(
            "SELECT uuid, name, world, x, y, z, pitch, yaw FROM homes WHERE uuid = ? ORDER BY name",
            (uuid,),
        )
        return [
            HomeData(uuid=r["uuid"], name=r["name"], world=r["world"],
                     x=r["x"], y=r["y"], z=r["z"], pitch=r["pitch"], yaw=r["yaw"])
            for r in rows
        ]

    async def delete_home(self, uuid: str, name: str) -> bool:
        cursor = await self._db.execute(
            "DELETE FROM homes WHERE uuid = ? AND name = ?",
            (uuid, name),
        )
        return cursor.rowcount > 0

    async def count_homes(self, uuid: str) -> int:
        return await self._db.fetchval(
            "SELECT COUNT(*) FROM homes WHERE uuid = ?",
            (uuid,),
        ) or 0

    async def home_exists(self, uuid: str, name: str) -> bool:
        val = await self._db.fetchval(
            "SELECT 1 FROM homes WHERE uuid = ? AND name = ?",
            (uuid, name),
        )
        return val is not None
