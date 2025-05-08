"""Number platform."""

from typing import cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .hub import Hub


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Add sensors for passed config_entry in HA."""
    hub = cast(Hub, config_entry.runtime_data)

    for zone in hub.zones.values():
        async_add_entities(
            zone.entity_bag.numbers,
            config_subentry_id=zone.config_subentry.subentry_id,
        )
