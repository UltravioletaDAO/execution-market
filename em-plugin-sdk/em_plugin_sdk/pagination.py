"""Auto-paginating async iterator for list endpoints."""

from __future__ import annotations

from typing import Any, AsyncIterator, Callable, Awaitable, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class PageIterator(AsyncIterator[T]):
    """Lazily fetches pages from a paginated EM API endpoint.

    Usage::

        async for task in client.tasks.list(status="published"):
            print(task.title)
    """

    def __init__(
        self,
        fetch_page: Callable[..., Awaitable[dict[str, Any]]],
        item_key: str,
        item_type: type[T],
        params: dict[str, Any],
        page_size: int = 20,
    ):
        self._fetch_page = fetch_page
        self._item_key = item_key
        self._item_type = item_type
        self._params = params
        self._page_size = page_size
        self._offset = params.get("offset", 0)
        self._buffer: list[T] = []
        self._exhausted = False

    def __aiter__(self) -> PageIterator[T]:
        return self

    async def __anext__(self) -> T:
        if not self._buffer:
            if self._exhausted:
                raise StopAsyncIteration
            await self._fetch_next_page()
            if not self._buffer:
                raise StopAsyncIteration
        return self._buffer.pop(0)

    async def _fetch_next_page(self) -> None:
        params = {**self._params, "limit": self._page_size, "offset": self._offset}
        data = await self._fetch_page(params)

        items = data.get(self._item_key, [])
        self._buffer = [self._item_type.model_validate(item) for item in items]
        self._offset += len(items)

        has_more = data.get("has_more", False)
        if not has_more or not items:
            self._exhausted = True

    async def collect(self) -> list[T]:
        """Collect all remaining items into a list."""
        result: list[T] = []
        async for item in self:
            result.append(item)
        return result
