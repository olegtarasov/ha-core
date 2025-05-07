"""Climate Manager integration."""

import logging
from typing import cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import SUBENTRY_TYPE_CIRCUIT, SUBENTRY_TYPE_ZONE
from .hub import Hub

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SENSOR,
]

type HubConfigEntry = ConfigEntry[Hub]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: HubConfigEntry) -> bool:
    """Set up Climate Manager Integration from a config entry."""

    config_entry.async_on_unload(
        config_entry.add_update_listener(_async_update_listener)
    )

    zones = [
        item
        for item in config_entry.subentries.values()
        if item.subentry_type == SUBENTRY_TYPE_ZONE
    ]
    circuits = [
        item
        for item in config_entry.subentries.values()
        if item.subentry_type == SUBENTRY_TYPE_CIRCUIT
    ]

    hub = Hub(hass, config_entry, zones, circuits)
    config_entry.runtime_data = hub

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    hub.initialize()

    return True


async def _async_update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    """Reload entities when configuration is updated."""

    # TODO: Find a way to remove Kp and Ki entities when PID changes to hysteresis
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Forward config entry unload to entities."""
    hub = cast(Hub, entry.runtime_data)

    hub.destroy()

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
