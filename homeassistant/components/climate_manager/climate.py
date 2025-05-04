"""Climate platform."""

from typing import cast

from homeassistant.helpers.entity import Entity
from homeassistant.const import UnitOfTemperature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.components.climate import ClimateEntity

from .common import DeviceInfoModel, HAEntityBase
from .hub import Hub
from .zone import Zone


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    hub = cast(Hub, config_entry.runtime_data)

    if hub.entity_bag.climates:
        async_add_entities(hub.entity_bag.climates)

    for zone in hub.zones.values():
        if zone.entity_bag.climates:
            async_add_entities(
                zone.entity_bag.climates,
                config_subentry_id=zone.config_subentry.subentry_id,
            )

    for circuit in hub.circuits.values():
        if circuit.entity_bag.climates:
            async_add_entities(
                circuit.entity_bag.climates,
                config_subentry_id=circuit.config_subentry.subentry_id,
            )
