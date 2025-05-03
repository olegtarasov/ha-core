"""Sensor platform."""

from typing import cast

from homeassistant.const import EntityCategory
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .zone import Zone
from .hub import Hub, HubBinarySensorBase


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    hub = cast(Hub, config_entry.runtime_data)

    # async_add_entities(hub.entity_bag.sensors)
    for zone in hub.zones:
        async_add_entities(
            zone.entity_bag.sensors,
            config_subentry_id=zone.config_subentry.subentry_id,
        )
