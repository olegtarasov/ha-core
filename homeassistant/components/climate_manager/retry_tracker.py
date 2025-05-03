from datetime import timedelta

from .utils import SimpleAwaiter


class RetryTracker:
    def __init__(self, start_delay=1, increase_factor=2, max_delay=16):
        self._max_delay = max_delay
        self._increase_factor = increase_factor
        self._start_delay = start_delay
        self._cur_delay = 0
        self._awaiter: SimpleAwaiter | None = None

    @property
    def is_fault(self) -> bool:
        return self._awaiter is not None

    @property
    def cur_delay(self) -> int:
        return self._cur_delay

    def set_fault(self) -> None:
        self._cur_delay = (
            min(self._cur_delay * self._increase_factor, self._max_delay)
            if self._awaiter is not None
            else self._start_delay
        )
        self._awaiter = SimpleAwaiter(timedelta(seconds=self._cur_delay))

    def reset_fault(self) -> None:
        self._awaiter = None
        self._cur_delay = 0

    @property
    def should_try(self) -> bool:
        return self._awaiter is None or self._awaiter.elapsed
