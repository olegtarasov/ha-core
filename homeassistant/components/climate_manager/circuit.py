"""Heating circuit controller."""

import logging

from homeassistant.components.climate import ClimateEntityFeature, HVACMode
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant

from .common import BinarySensorBase, ClimateBase, ControllerBase, DeviceInfoModel
from .const import CONFIG_SWITCHES
from .zone import Zone

_LOGGER = logging.getLogger(__name__)


class Circuit(ControllerBase):
    """Heating circuit."""

    def __init__(
        self,
        hass: HomeAssistant,
        circuit_config: ConfigSubentry,
        zones: list[Zone],
    ) -> None:
        """Init heating circuit."""
        super().__init__(hass, circuit_config.title)

        self.zones = zones

        # Device
        self.device_info = DeviceInfoModel(
            self._name, self._unique_id, "Heating Circuit"
        )

        # Config
        self.config_subentry = circuit_config

        config_data = circuit_config.data.copy()
        self._switches = config_data.get(CONFIG_SWITCHES, [])

        # Entities
        self.circuit_active_sensor = self.entity_bag.add_binary_sensor(
            CircuitActiveSensor(self.device_info)
        )
        self.climate = self.entity_bag.add_climate(CircuitClimate(self))

    async def control_circuit(self) -> None:
        """Control the heating circuit."""
        cur_temp: float | None = None
        target_temps: set[float] = set()
        hvac_modes: set[HVACMode] = set()
        preset_modes: set[str] = set()
        any_output = False

        for zone in self.zones:
            if zone.current_temperature:
                cur_temp = (
                    min(cur_temp, zone.current_temperature)
                    if cur_temp
                    else zone.current_temperature
                )
            if zone.climate_entity.target_temperature:
                target_temps.add(zone.climate_entity.target_temperature)
            if zone.climate_entity.hvac_mode:
                hvac_modes.add(zone.climate_entity.hvac_mode)
            if zone.climate_entity.preset_mode:
                preset_modes.add(zone.climate_entity.preset_mode)
            any_output = any_output or zone.regulator_output > 0

        self.climate.set_current_temperature(cur_temp)
        self.climate.set_target_temperature_no_notify(
            target_temps.pop() if len(target_temps) == 1 else None
        )
        self.climate.set_hvac_mode_no_notify(
            hvac_modes.pop() if len(hvac_modes) == 1 else None
        )
        self.climate.set_preset_mode_no_notify(
            preset_modes.pop() if len(preset_modes) == 1 else None
        )

        await self.set_active(any_output)

    async def set_active(self, value: bool) -> None:
        """Set heating circuit as active."""
        for sw in self._switches:
            await self._hass.services.async_call(
                "switch",  # domain
                "turn_on" if value else "turn_off",  # service
                {"entity_id": sw},
            )

        self.circuit_active_sensor.set_is_on(value)

    async def handle_target_temperature_changed(self, value: float) -> None:
        """Handle target temperature being changed from UI."""
        for zone in self.zones:
            await zone.set_target_temperature_from_circuit(value)

    async def handle_hvac_mode_changed(self, value: HVACMode) -> None:
        """Handle HVAC mode being changed from UI."""
        for zone in self.zones:
            await zone.set_hvac_mode_from_circuit(value)

    async def handle_preset_changed(self, value: str) -> None:
        """Handle preset being changed from UI."""
        for zone in self.zones:
            await zone.set_preset_from_circuit(value)


class CircuitActiveSensor(
    BinarySensorBase
):  # pylint: disable=hass-enforce-class-module
    """Circuit active sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, device_info: DeviceInfoModel) -> None:
        """Init circuit active sensor."""
        super().__init__("Active", device_info)


class CircuitClimate(ClimateBase):  # pylint: disable=hass-enforce-class-module
    """Circuit climate."""

    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    _attr_target_temperature_high = None
    _attr_target_temperature_low = None

    def __init__(self, circuit: Circuit) -> None:
        """Initialize the circuit climate."""
        super().__init__("Climate", circuit.device_info)
        self.circuit = circuit

    def set_target_temperature_no_notify(self, value: float | None) -> None:
        """Update the target temperature without triggering an update."""
        self._attr_target_temperature = value
        self.schedule_update_ha_state()

    def set_target_temperature_high_no_notify(self, value: float | None) -> None:
        """Update the high target temperature without triggering an update."""
        self._attr_target_temperature_high = value
        self.schedule_update_ha_state()

    def set_target_temperature_low_no_notify(self, value: float | None) -> None:
        """Update the low target temperature without triggering an update."""
        self._attr_target_temperature_low = value
        self.schedule_update_ha_state()

    def set_hvac_mode_no_notify(self, hvac_mode: HVACMode | None) -> None:
        """Update the HVAC mode without triggering an update."""
        self._attr_hvac_mode = hvac_mode
        self.schedule_update_ha_state()

    def set_preset_mode_no_notify(self, preset_mode: str | None) -> None:
        """Update the preset mode without triggering an update."""
        self._attr_preset_mode = preset_mode
        self.schedule_update_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the HVAC mode and notify the circuit."""
        self._attr_hvac_mode = hvac_mode
        self.async_write_ha_state()
        await self.circuit.handle_hvac_mode_changed(hvac_mode)

    async def async_set_temperature(self, **kwargs) -> None:
        """Set the temperature and notify the circuit."""
        if (temp := kwargs.get("temperature")) is not None:
            self._attr_target_temperature = float(temp)
            self.async_write_ha_state()
            await self.circuit.handle_target_temperature_changed(
                self._attr_target_temperature
            )

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode and notify the circuit."""
        self._attr_preset_mode = preset_mode
        self.async_write_ha_state()
        await self.circuit.handle_preset_changed(preset_mode)
