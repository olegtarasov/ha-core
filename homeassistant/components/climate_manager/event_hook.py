import asyncio
from typing import Any


class EventHook(object):

    def __init__(self):
        self.__handlers = []

    def __iadd__(self, handler):
        self.__handlers.append(handler)
        return self

    def __isub__(self, handler):
        self.__handlers.remove(handler)
        return self

    async def _corofire(self, *a, **kw) -> list[Any]:
        results, awaitables = [], []
        for handler in list(self.__handlers):
            result = handler(*a, **kw)
            if asyncio.iscoroutine(result):
                awaitables.append(result)
            else:
                results.append(result)

        if awaitables:
            results.extend(await asyncio.gather(*awaitables))

        return results

    def fire(self, *a, **kw) -> list[Any]:
        """
        Synchronous entry point.

        * If no event loop is running (typical sync program) → create a
          temporary loop via `asyncio.run`.
        * If already inside an event loop (e.g. you called from a Jupyter
          cell) → run the coroutine in that loop *synchronously* with
          `run_until_complete`.  Nested loops are forbidden, so we fall
          back to `asyncio.create_task` + `loop.run_until_complete`.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # no loop yet
            return asyncio.run(self._corofire(*a, **kw))

        # We *are* in a loop already → run coroutine in-loop
        fut = asyncio.ensure_future(self._corofire(*a, **kw), loop=loop)
        loop.run_until_complete(fut)
        return fut.result()

    async def async_fire(self, *a, **kw) -> list[Any]:
        """Async entry point – just await the core coroutine."""
        return await self._corofire(*a, **kw)
