from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


class EconomyAPI:

    def __init__(self) -> None:
        self._plugin = None

    def set_plugin(self, plugin) -> None:
        self._plugin = plugin

    async def get_balance(self, uuid: str) -> float:
        if self._plugin is None:
            return 0.0
        try:
            import asyncio
            future = self._plugin.run_async(self._plugin.economy_service.get_balance(uuid))
            return await asyncio.wrap_future(future)
        except Exception as e:
            if hasattr(self, "_logger") and self._logger:
                self._logger.error(f"EconomyAPI error (get_balance): {e}")
            return 0.0

    async def add_balance(self, uuid: str, amount: float) -> float:
        if self._plugin is None:
            return 0.0
        import asyncio
        future = self._plugin.run_async(self._plugin.economy_service.add_balance(uuid, amount))
        return await asyncio.wrap_future(future)

    async def remove_balance(self, uuid: str, amount: float) -> float | None:
        if self._plugin is None:
            return None
        import asyncio
        future = self._plugin.run_async(self._plugin.economy_service.remove_balance(uuid, amount))
        return await asyncio.wrap_future(future)

    async def set_balance(self, uuid: str, amount: float) -> float:
        if self._plugin is None:
            return 0.0
        import asyncio
        future = self._plugin.run_async(self._plugin.economy_service.set_balance(uuid, amount))
        return await asyncio.wrap_future(future)

    async def has_balance(self, uuid: str, amount: float) -> bool:
        balance = await self.get_balance(uuid)
        return balance >= amount

    @property
    def currency_symbol(self) -> str:
        if self._plugin is None:
            return "$"
        return getattr(self._plugin.economy_service, "currency_symbol", "$")
