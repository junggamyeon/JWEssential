from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from jwessentials.database.database_manager import DatabaseManager

if TYPE_CHECKING:
    from endstone.level import Location


@dataclass(frozen=True, slots=True)
class WarpData:
    name: str
    world: str
    x: float
    y: float
    z: float
    pitch: float
    yaw: float
    category: str


@dataclass(frozen=True, slots=True)
class SpawnData:
    world: str
    x: float
    y: float
    z: float
    pitch: float
    yaw: float


class WarpRepository:

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def set_warp(self, name: str, location: Location, category: str = "general", created_by: str | None = None) -> None:
        await self._db.execute(
            """
            INSERT INTO warps (name, world, x, y, z, pitch, yaw, category, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                world = excluded.world,
                x = excluded.x,
                y = excluded.y,
                z = excluded.z,
                pitch = excluded.pitch,
                yaw = excluded.yaw,
                category = excluded.category
            """,
            (name, location.dimension.name, location.x, location.y, location.z,
             location.pitch, location.yaw, category, created_by),
        )

    async def get_warp(self, name: str) -> WarpData | None:
        row = await self._db.fetchone(
            """
            SELECT name, world, x, y, z, pitch, yaw, category
            FROM warps WHERE name = ?
            """,
            (name,),
        )
        if row is None:
            return None
        return WarpData(
            name=row["name"],
            world=row["world"],
            x=row["x"],
            y=row["y"],
            z=row["z"],
            pitch=row["pitch"],
            yaw=row["yaw"],
            category=row["category"],
        )

    async def get_all_warps(self, category: str | None = None) -> list[WarpData]:
        query = "SELECT name, world, x, y, z, pitch, yaw, category FROM warps"
        params: tuple = ()
        if category:
            query += " WHERE category = ?"
            params = (category,)
        query += " ORDER BY name"
        rows = await self._db.fetchall(query, params)
        return [
            WarpData(
                name=r["name"], world=r["world"], x=r["x"], y=r["y"],
                z=r["z"], pitch=r["pitch"], yaw=r["yaw"], category=r["category"],
            )
            for r in rows
        ]

    async def delete_warp(self, name: str) -> bool:
        cursor = await self._db.execute(
            "DELETE FROM warps WHERE name = ?",
            (name,),
        )
        return cursor.rowcount > 0

    async def warp_exists(self, name: str) -> bool:
        val = await self._db.fetchval(
            "SELECT 1 FROM warps WHERE name = ?",
            (name,),
        )
        return val is not None

    async def get_warp_count(self) -> int:
        return await self._db.fetchval(
            "SELECT COUNT(*) FROM warps"
        ) or 0


class SpawnRepository:

    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def set_spawn(self, location: Location) -> None:
        await self._db.execute(
            """
            INSERT INTO spawn (id, world, x, y, z, pitch, yaw)
            VALUES (1, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                world = excluded.world,
                x = excluded.x,
                y = excluded.y,
                z = excluded.z,
                pitch = excluded.pitch,
                yaw = excluded.yaw
            """,
            (location.dimension.name, location.x, location.y, location.z,
             location.pitch, location.yaw),
        )

    async def get_spawn(self) -> SpawnData | None:
        row = await self._db.fetchone(
            "SELECT world, x, y, z, pitch, yaw FROM spawn WHERE id = 1"
        )
        if row is None:
            return None
        return SpawnData(
            world=row["world"],
            x=row["x"],
            y=row["y"],
            z=row["z"],
            pitch=row["pitch"],
            yaw=row["yaw"],
        )
