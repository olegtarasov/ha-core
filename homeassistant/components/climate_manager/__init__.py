"""Climate Manager integration."""

import logging
from typing import cast

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from .const import DOMAIN, SUBENTRY_TYPE_CIRCUIT, SUBENTRY_TYPE_ZONE
from .hub import Hub

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.NUMBER,
    Platform.SENSOR,
    # Platform.SWITCH,
]

type HubConfigEntry = ConfigEntry[Hub]

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, config_entry: HubConfigEntry) -> bool:
    """Set up Example Integration from a config entry."""

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

    _LOGGER.info("=== Before forward entity setups on load")
    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    _LOGGER.info("=== After forwarding entity setups")

    _LOGGER.info("=== Before hub init on load")
    hub.initialize()
    _LOGGER.info("=== After hub init")

    return True


async def _async_update_listener(hass: HomeAssistant, config_entry: ConfigEntry):
    # TODO: Find a way to remove Kp and Ki entities when PID changes to hysteresis
    await hass.config_entries.async_reload(config_entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hub = cast(Hub, entry.runtime_data)

    _LOGGER.info("=== Before hub destroy on unload")
    hub.destroy()
    _LOGGER.info("=== After hub destroy on unload")

    _LOGGER.info("=== Before unloading platforms")
    result = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    _LOGGER.info("=== After unloading platforms: %s", result)
    return result
