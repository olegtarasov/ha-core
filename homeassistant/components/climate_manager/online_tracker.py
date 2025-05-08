"""Online tracker."""

import asyncio
from collections.abc import Awaitable, Callable
from datetime import timedelta
import logging

from .common import BinarySensorBase
from .utils import SimpleAwaiter

_LOGGER = logging.getLogger(__name__)


class OnlineTracker:
    """Track the online status of a sensor and handle offline events."""

    def __init__(
        self,
        fault_entity: BinarySensorBase,
        wait_interval: timedelta,
        sensor_name: str,
        became_offline_callback: Callable[[], Awaitable[None] | None] | None,
    ) -> None:
        """Initialize the OnlineTracker with necessary parameters."""
        self._wait_interval = wait_interval
        self._fault_entity = fault_entity
        self._sensor_name = sensor_name
        self._became_offline_callback = became_offline_callback
        self._awaiter: SimpleAwaiter | None = None

    async def is_online(self, online_raw: bool) -> bool:
        """Determine if the sensor is online, considering fault states and wait intervals."""
        if not online_raw:
            if self._fault_entity.is_on:
                # Fault is already set, wait for sensor to become online and do nothing
                return False
            if not self._awaiter:
                # This is a new development. Try to wait for _wait_interval for sensor to come online
                _LOGGER.info(
                    "%s became offline, waiting for %s to resolve itself",
                    self._sensor_name,
                    self._wait_interval,
                )
                self._awaiter = SimpleAwaiter(self._wait_interval)

                return True  # We are still assuming sensor is OK, just temporarily disconnected

            if self._awaiter.elapsed:
                # Sensor didn't come back in _wait_interval, let's report it offline and fire a callback
                self._awaiter = None
                _LOGGER.warning(
                    "%s didn't come back in %s",
                    self._sensor_name,
                    self._wait_interval,
                )
                if self._became_offline_callback:
                    cr = self._became_offline_callback()
                    if asyncio.iscoroutine(cr):
                        await cr

                self._fault_entity.set_is_on(True)

                return False  # Nope, its offline

            return True  # Still giving it a chance while awaiter has not elapsed

        if self._fault_entity.is_on:
            _LOGGER.info("%s has come back after the fault state", self._sensor_name)
            self._fault_entity.set_is_on(False)
        if self._awaiter is not None:
            _LOGGER.info(
                "%s has come back in less than %s",
                self._sensor_name,
                self._wait_interval,
            )

        self._awaiter = None

        return True  # Definitely online
