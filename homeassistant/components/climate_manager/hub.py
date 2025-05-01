"""Hub."""

from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_interval

_LOGGER = logging.getLogger(__name__)


class Hub:
    """Hub."""

    def __init__(
        self,
        hass: HomeAssistant,
        hub_config: dict[str, Any],
        zones_config: list[dict[str, Any]],
    ) -> None:
        self.hass = hass

        self._unsubscribe = async_track_time_interval(
            hass, self._async_update_from_foo, timedelta(seconds=1)
        )

    async def _async_update_from_foo(self, _now: datetime) -> None:
        """Fetch sensor.foo, double it, and push state to HA."""
        _LOGGER.info("Tick")
        # foo = self.hass.states.get("sensor.foo")
        # if foo and foo.state not in (None, "", "unknown", "unavailable"):
        #     try:
        #         self._native_value = float(foo.state) * 2
        #     except (ValueError, TypeError):
        #         _LOGGER.warning("sensor.foo contains non-numeric value: %s", foo.state)
        #         self._native_value = None
        # else:
        #     self._native_value = None

        # # Tell Home Assistant the value changed (or became None)
        # self.async_write_ha_state()
