"""Binary sensor platform."""

from typing import cast

from homeassistant.const import EntityCategory
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .zone import Zone
from .hub import Hub
from homeassistant.components.binary_sensor import BinarySensorDeviceClass


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    hub = cast(Hub, config_entry.runtime_data)

    if hub.entity_bag.binary_sensors:
        async_add_entities(hub.entity_bag.binary_sensors)
    for zone in hub.zones.values():
        if zone.entity_bag.binary_sensors:
            async_add_entities(
                zone.entity_bag.binary_sensors,
                config_subentry_id=zone.config_subentry.subentry_id,
            )

    for circuit in hub.circuits.values():
        if circuit.entity_bag.binary_sensors:
            async_add_entities(
                circuit.entity_bag.binary_sensors,
                config_subentry_id=circuit.config_subentry.subentry_id,
            )
