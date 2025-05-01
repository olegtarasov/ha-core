"""Climate Manager integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN, SUBENTRY_TYPE_ZONE
from .hub import Hub

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    # Platform.CLIMATE,
    # Platform.NUMBER,
    # Platform.SENSOR,
    # Platform.SWITCH,
]

type HubConfigEntry = ConfigEntry[Hub]


async def async_setup_entry(hass: HomeAssistant, config_entry: HubConfigEntry) -> bool:
    """Set up Example Integration from a config entry."""

    zones = [
        item
        for item in config_entry.subentries.values()
        if item.subentry_type == SUBENTRY_TYPE_ZONE
    ]

    config_entry.runtime_data = Hub(hass, config_entry, zones)

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
