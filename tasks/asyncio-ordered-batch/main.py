import asyncio
from collections.abc import Awaitable, Callable, Sequence


async def run_batch(
    items: Sequence[int],
    work: Callable[[int], Awaitable[int]],
) -> list[int | Exception]:
    if not items:
        return []

    async def _run(item: int) -> int | Exception:
        try:
            return await work(item)
        except Exception as exc:
            return exc

    tasks = [asyncio.create_task(_run(item)) for item in items]
    try:
        return list(await asyncio.gather(*tasks))
    except asyncio.CancelledError:
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
