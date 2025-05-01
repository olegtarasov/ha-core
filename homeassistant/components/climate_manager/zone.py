"""Heating zone."""

from homeassistant.config_entries import ConfigSubentry

from .common import ClimateDeviceInfo, ClimateEntityBase
from .const import CONFIG_TEMPERATURE_SENSOR, CONFIG_TRVS, CONFIG_WINDOW_SENSORS


class Zone(ClimateEntityBase):
    """Heating zone."""

    def __init__(self, zone_config: ConfigSubentry) -> None:
        super().__init__(zone_config.title)

        config_data = zone_config.data.copy()
        self.temp_sensor = zone_config.data[CONFIG_TEMPERATURE_SENSOR]
        self.trvs = config_data[CONFIG_TRVS] if CONFIG_TRVS in config_data else []
        self.windows = config_data[CONFIG_WINDOW_SENSORS] if CONFIG_WINDOW_SENSORS in config_data else []

        self.device_info = ClimateDeviceInfo(self.name, self.unique_id, "Virtual Room Thermostat")

