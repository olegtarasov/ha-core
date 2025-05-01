"""Hub."""

from datetime import datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .common import ClimateDeviceInfo, ClimateEntityBase
from .zone import Zone

_LOGGER = logging.getLogger(__name__)

class Hub(ClimateEntityBase):
    """Hub."""

    def __init__(
        self,
        hass: HomeAssistant,
        hub_config: ConfigEntry,
        zones_config: list[ConfigSubentry],
    ) -> None:
        super().__init__(hub_config.title)
        self.hass = hass
        self._unsubscribe = None

        config_data = hub_config.data.copy()

        self.zones = [Zone(zone_config) for zone_config in zones_config]

        self.device_info = ClimateDeviceInfo(self.name, self.unique_id, "Virtual Room Thermostat")


    async def async_added_to_hass(self) -> None:
        self._unsubscribe = async_track_time_interval(
            self.hass, self._async_control_heating, timedelta(seconds=1)
        )

    async def async_will_remove_from_hass(self) -> None:
        """Clean up the listener when the entity is removed."""
        if self._unsubscribe:
            self._unsubscribe()

    async def _async_control_heating(self, _now: datetime) -> None:
        _LOGGER.info("Tick")
