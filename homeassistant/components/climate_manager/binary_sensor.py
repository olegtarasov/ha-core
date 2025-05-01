"""Binary sensor platform."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HubConfigEntry
from .common import HubBinarySensorBase
from .hub import Hub


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: HubConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    hub = config_entry.runtime_data

    async_add_entities([HubFaultSensor(hub)])


class HubFaultSensor(HubBinarySensorBase):
    def __init__(self, hub: Hub):
        super().__init__("Fault", hub)

        self._attr_is_on = False

