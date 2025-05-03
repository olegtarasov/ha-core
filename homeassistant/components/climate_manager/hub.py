"""Hub."""

import logging
from datetime import datetime, timedelta

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.components.climate import (
    ClimateEntity,
    HVACMode,
    PRESET_HOME,
)
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from .common import (
    BinarySensorBase,
    ClimateEntityBase,
    ControllerBase,
    DeviceInfoModel,
    FaultSensor,
    HAEntityBase,
)
from .zone import Zone

_LOGGER = logging.getLogger(__name__)


class Hub(ControllerBase):
    """Hub."""

    def __init__(
        self,
        hass: HomeAssistant,
        hub_config: ConfigEntry,
        zones_config: list[ConfigSubentry],
    ) -> None:
        super().__init__(hass, hub_config.title)

        # Config
        config_data = hub_config.data.copy()
        self.zones = [Zone(hass, zone_config) for zone_config in zones_config]

        # Device
        self.device_info = DeviceInfoModel(
            self._name, self._unique_id, "Virtual Room Thermostat"
        )

        # Entities
        self.climate_entity = self.entity_bag.add_climate(HubClimate(self))
        self.fault_entity = self.entity_bag.add_binary_sensor(
            FaultSensor(self.device_info)
        )

        # Private
        self._unsubscribe = None

    async def _async_control_heating(self, _now: datetime) -> None:
        for zone in self.zones:
            await zone.async_control_temperature()

    def initialize(self):
        for zone in self.zones:
            zone.initialize()

        self._unsubscribe = async_track_time_interval(
            self._hass, self._async_control_heating, timedelta(seconds=1)
        )

    def destroy(self):
        if self._unsubscribe:
            self._unsubscribe()


class HubBinarySensorBase(BinarySensorBase):
    def __init__(self, name: str, hub: Hub):
        super().__init__(name, hub.device_info)
        self.hub = hub


class HubFaultSensor(HubBinarySensorBase):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, hub: Hub):
        super().__init__("Fault", hub)

        self._attr_is_on = False


class HubClimate(ClimateEntityBase):
    def __init__(self, hub: Hub):
        super().__init__("Climate", hub.device_info)
        self.hub = hub

    @property
    def hvac_mode(self) -> HVACMode:
        return HVACMode.HEAT

    @property
    def preset_mode(self) -> str | None:
        return PRESET_HOME
