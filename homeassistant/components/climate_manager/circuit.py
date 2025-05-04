from homeassistant.const import EntityCategory
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant

from .common import BinarySensorBase, ClimateBase, ControllerBase, DeviceInfoModel
from .const import CONFIG_SWITCHES
from homeassistant.components.climate import HVACMode, PRESET_HOME
from .utils import get_state_bool
from .zone import Zone


class Circuit(ControllerBase):
    def __init__(
        self,
        hass: HomeAssistant,
        circuit_config: ConfigSubentry,
        zones: list[Zone],
    ):
        super().__init__(hass, circuit_config.title)

        self.zones = zones

        # Device
        self.device_info = DeviceInfoModel(
            self._name, self._unique_id, "Heating Circuit"
        )

        # Config
        self.config_subentry = circuit_config

        config_data = circuit_config.data.copy()
        self._switches = (
            config_data[CONFIG_SWITCHES] if CONFIG_SWITCHES in config_data else []
        )

        # Entities
        self.circuit_active_sensor = self.entity_bag.add_binary_sensor(
            CircuitActiveSensor(circuit_config.title, self.device_info)
        )
        self.climate = self.entity_bag.add_climate(CircuitClimate(self.device_info))

    def control_circuit(self) -> None:
        cur_temp: float | None = None
        target_temp: float | None = None
        hvac_mode: HVACMode | None = self.zones[0].climate_entity.hvac_mode
        preset_mode: str | None = self.zones[0].climate_entity.preset_mode
        any_trv_open = False

        for zone in self.zones:
            if zone.current_temperature:
                cur_temp = (
                    min(cur_temp, zone.current_temperature)
                    if cur_temp
                    else zone.current_temperature
                )
            if zone.target_temperature is not None:
                target_temp = (
                    min(target_temp, zone.target_temperature)
                    if target_temp is not None
                    else zone.target_temperature
                )
            if hvac_mode != zone.climate_entity.hvac_mode:
                hvac_mode = None
            if preset_mode != zone.climate_entity.preset_mode:
                preset_mode = None
            any_trv_open = any_trv_open or (
                zone.trv_entity.is_on if zone.trv_entity else False
            )

        self.climate.set_current_temperature(cur_temp)
        self.climate.set_target_temperature(target_temp)
        self.climate.set_hvac_mode(hvac_mode)
        self.climate.set_preset_mode(preset_mode)

        self.set_active(any_trv_open)

    def set_active(self, value: bool) -> None:
        for sw in self._switches:
            self._hass.services.call(
                "switch",  # domain
                "turn_on" if value else "turn_off",  # service
                {"entity_id": sw},
            )

        self.circuit_active_sensor.set_is_on(value)


class CircuitActiveSensor(BinarySensorBase):

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, name: str, device_info: DeviceInfoModel):
        super().__init__(name, device_info)


class CircuitClimate(ClimateBase):
    def __init__(self, device_info):
        super().__init__("Climate", device_info)

    def set_target_temperature(self, value: float) -> None:
        self._attr_target_temperature = value
        self.schedule_update_ha_state()

    def set_hvac_mode(self, hvac_mode: HVACMode | None) -> None:
        self._attr_hvac_mode = hvac_mode

    def set_preset_mode(self, preset_mode: str | None) -> None:
        self._attr_preset_mode = preset_mode
