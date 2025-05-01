"""Binary sensor platform."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HubConfigEntry


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: HubConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    hub = config_entry.runtime_data

    new_devices = []
    # for roller in hub.rollers:
    #     new_devices.append(BatterySensor(roller))
    #     new_devices.append(IlluminanceSensor(roller))
    # if new_devices:
    #     async_add_entities(new_devices)
