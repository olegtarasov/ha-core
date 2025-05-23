"""Heating zone."""

from collections.abc import Callable
from datetime import timedelta
import logging
from typing import Any, cast

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.climate import HVACMode
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.restore_state import RestoreEntity

from .common import (
    BinarySensorBase,
    ClimateBase,
    ControllerBase,
    DeviceInfoModel,
    SensorBase,
)
from .const import (
    CONFIG_REGULATOR_TYPE,
    CONFIG_TEMPERATURE_SENSOR,
    CONFIG_TRVS,
    CONFIG_WINDOW_SENSORS,
    REGULATOR_TYPE_PID,
)
from .online_tracker import OnlineTracker
from .regulator import HysteresisRegulator, PidRegulator, RegulatorBase
from .utils import get_state_float
from .window import ZoneWindow

_LOGGER = logging.getLogger(__name__)


class Zone(ControllerBase):
    """Heating zone."""

    _regulator: RegulatorBase

    def __init__(self, hass: HomeAssistant, zone_config: ConfigSubentry) -> None:
        """Initialize the heating zone."""
        super().__init__(hass, zone_config.title)

        # Device
        self.device_info = DeviceInfoModel(
            self._name, self._unique_id, "Zone Thermostat"
        )

        # Config
        self.config_subentry = zone_config

        config_data = zone_config.data.copy()

        self._regulator_type = zone_config.data[CONFIG_REGULATOR_TYPE]
        self._temp_sensor = zone_config.data[CONFIG_TEMPERATURE_SENSOR]
        self._trvs = config_data.get(CONFIG_TRVS, [])
        self._window: ZoneWindow | None = (
            ZoneWindow(
                hass,
                config_data[CONFIG_WINDOW_SENSORS],
                self.device_info,
                self.entity_bag,
            )
            if CONFIG_WINDOW_SENSORS in config_data
            and len(config_data[CONFIG_WINDOW_SENSORS]) > 0
            else None
        )

        # Entities
        self.climate_entity = self.entity_bag.add_climate(ZoneClimate(self))
        self.sensor_fault_entity = self.entity_bag.add_binary_sensor(
            ZoneSensorFaultSensor(self.device_info)
        )
        self.control_fault_entity = self.entity_bag.add_binary_sensor(
            ZoneControlFaultSensor(self.device_info)
        )
        self.output_entity = self.entity_bag.add_sensor(
            ZoneOutputSensor(self.device_info)
        )
        self.trv_entity = (
            self.entity_bag.add_binary_sensor(ZoneTrvSensor(self.device_info))
            if self._trvs
            else None
        )
        self.regulator_active_entity = self.entity_bag.add_binary_sensor(
            ZoneRegulatorActiveSensor(self.device_info)
        )

        # Private
        if config_data[CONFIG_REGULATOR_TYPE] == REGULATOR_TYPE_PID:
            pid = PidRegulator(self.entity_bag, self.device_info)
            pid.on_coeffs_changed += self._handle_pid_coeffs_changed
            self._regulator = pid
        else:
            self._regulator = HysteresisRegulator()

        self._regulator_enablers: list[Callable[[], bool]] = [
            self._climate_enabled,
            self._no_sensor_fault,
        ]
        if self._window:
            self._regulator_enablers.append(self._window.should_heat)

        self._sensor_online_tracker = OnlineTracker(
            self.sensor_fault_entity,
            timedelta(seconds=5),
            f"{self._name} temperature",
            None,
        )

    def initialize(self) -> None:
        """Initialize the heating zone's regulator."""
        self._regulator.initialize(self.climate_entity.target_temperature)

    @property
    def current_temperature(self) -> float | None:
        """Get the current temperature of the zone."""
        return get_state_float(self._hass, self._temp_sensor)

    @property
    def target_temperature(self) -> float | None:
        """Get the target temperature set for the zone."""
        return self.climate_entity.target_temperature

    @property
    def regulator_output(self) -> float:
        """Get the output value from the regulator."""
        return self._regulator.output

    async def control_temperature(self) -> None:
        """Control the temperature of the zone based on current conditions."""
        try:
            cur_temp = self.current_temperature

            # If the sensor remains offline for longer than 5 sec, fault entity will be set
            await self._sensor_online_tracker.is_online(cur_temp is not None)

            # If there is a fault or a window is open, we disable PID
            self._recalculate_regulator_enabled()

            # The temp sensor can be temporarily offline, but we give it a chance to recover without pausing PID.
            if cur_temp:
                self.climate_entity.set_current_temperature(cur_temp)
                if self._regulator.enabled:
                    self._regulator.calculate_output(cur_temp)

            output = self._regulator.output
            self.output_entity.set_native_value(output)

            # Operate TRVs
            if self._trvs:
                # If windows are open, save TRV batteries and do nothing
                if self._regulator.enabled and (
                    not self._window or self._window.should_heat()
                ):
                    await self.operate_trvs(output)

            # If we reached here, we recovered from a previous unexpected fault. Clear the fault sensor and log
            if self.control_fault_entity.is_on:
                _LOGGER.info("Zone %s recovered from control fault", self._name)
                self.control_fault_entity.set_is_on(False)
        except Exception:
            # Function is called every second, and we don't want to spam the logs
            if not self.control_fault_entity.is_on:
                _LOGGER.exception(
                    "Exception occured while trying to control heating in zone %s",
                    self._name,
                )
                self.control_fault_entity.set_is_on(True)

    async def operate_trvs(self, output: float) -> None:
        """Operate the TRVs based on the regulator output."""
        mode = "heat" if output > 0 else "off"
        for trv in self._trvs:
            await self._hass.services.async_call(
                "climate", "set_hvac_mode", {"entity_id": trv, "hvac_mode": mode}
            )

        if self.trv_entity:
            self.trv_entity.set_is_on(output > 0)

    async def set_target_temperature_from_circuit(self, value: float) -> None:
        """Set target temperature through climate entity as if initiated from UI."""
        await self.climate_entity.async_set_temperature(temperature=value)

    async def set_hvac_mode_from_circuit(self, value: HVACMode) -> None:
        """Set HVAC mode through climate entity as if initiated from UI."""
        await self.climate_entity.async_set_hvac_mode(value)

    async def set_preset_from_circuit(self, value: str) -> None:
        """Set preset through climate entity as if initiated from UI."""
        await self.climate_entity.async_set_preset_mode(value)

    def _recalculate_regulator_enabled(self):
        """Recalculate whether the regulator is enabled based on current conditions."""
        result = True
        for enabler in self._regulator_enablers:
            result = result and enabler()

        self._regulator.enabled = result
        self.regulator_active_entity.set_is_on(result)

    def _climate_enabled(self):
        """Check if the climate entity is enabled for heating."""
        return self.climate_entity.hvac_mode == HVACMode.HEAT

    def _no_sensor_fault(self):
        """Check if there is no sensor fault detected."""
        return not self.sensor_fault_entity.is_on

    def handle_target_temperature_changed(self, value: float) -> None:
        """Handle changes in target temperature for the regulator."""
        self._regulator.target_temperature = value

    def handle_preset_changed(self, preset: dict[str, Any]):
        """Handle changes in preset values for the PID regulator."""
        # Climate entity applies its own preset values, we just need to handle other entities
        if isinstance(self._regulator, PidRegulator):
            pid = cast(PidRegulator, self._regulator)
            if (kp := preset.get("kp")) is not None:
                pid.kp = float(kp)
            if (ki := preset.get("ki")) is not None:
                pid.ki = float(ki)

        if (temp := preset.get("temperature")) is not None:
            self._regulator.target_temperature = float(temp)

        # Reset the regulator when preset is applied.
        self._regulator.reset()

    def _handle_pid_coeffs_changed(self):
        """Handle changes in PID coefficients for the regulator."""
        pid = cast(PidRegulator, self._regulator)
        self.climate_entity.save_pid_coeffs(pid.kp, pid.ki)


class ZoneControlFaultSensor(
    BinarySensorBase
):  # pylint: disable=hass-enforce-class-module
    """Sensor to indicate control faults in the zone."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, device_info: DeviceInfoModel) -> None:
        """Initialize the control fault sensor."""
        super().__init__("Control Fault", device_info)


class ZoneSensorFaultSensor(
    BinarySensorBase
):  # pylint: disable=hass-enforce-class-module
    """Sensor to indicate sensor faults in the zone."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, device_info: DeviceInfoModel) -> None:
        """Initialize the sensor fault sensor."""
        super().__init__("Sensor Fault", device_info)


class ZoneRegulatorActiveSensor(
    BinarySensorBase
):  # pylint: disable=hass-enforce-class-module
    """Sensor to indicate whether regulator is active."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = BinarySensorDeviceClass.RUNNING

    def __init__(self, device_info: DeviceInfoModel) -> None:
        """Initialize the sensor fault sensor."""
        super().__init__("Regulator Active", device_info)


class ZoneClimate(
    ClimateBase, RestoreEntity
):  # pylint: disable=hass-enforce-class-module
    """Climate entity for the heating zone."""

    _attr_target_temperature = 22
    _attr_min_temp = 18
    _attr_max_temp = 32

    def __init__(self, zone: Zone) -> None:
        """Initialize the climate entity for the zone."""
        super().__init__("Climate", zone.device_info)
        self.zone = zone

        self._presets: dict[str, dict[str, Any]] = {}

    async def async_added_to_hass(self) -> None:
        """Initialize the climate entity when added to Home Assistant."""
        await super().async_added_to_hass()

        if (last := await self.async_get_last_state()) is None:
            return

        # state itself is the last hvac_mode
        if last.state in self._attr_hvac_modes:
            self._attr_hvac_mode = HVACMode(last.state)

        attrs = last.attributes
        if (presets := attrs.get("presets")) is not None:
            self._presets = presets

        if (tmp := attrs.get("temperature")) is not None:
            self._attr_target_temperature = float(tmp)

        if (preset := attrs.get("preset_mode")) in self._attr_preset_modes:
            self._attr_preset_mode = preset

    @property
    def extra_state_attributes(self) -> dict:
        """Get extra state attributes for the climate entity."""
        return {
            "presets": self._presets,
        }

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set the HVAC mode for the climate entity."""
        self._attr_hvac_mode = hvac_mode
        self._set_preset_item("mode", str(self._attr_hvac_mode))
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs) -> None:
        """Set the temperature for the climate entity."""
        if (temp := kwargs.get("temperature")) is not None:
            self._attr_target_temperature = float(temp)
            self._set_preset_item("temperature", self._attr_target_temperature)

            self.async_write_ha_state()
            self.zone.handle_target_temperature_changed(float(temp))

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode for the climate entity."""
        self._attr_preset_mode = preset_mode
        self.async_write_ha_state()

        if preset_mode in self._presets:
            self._apply_preset(self._presets[preset_mode])

    def save_pid_coeffs(self, kp: float, ki: float):
        """Save PID coefficients for the preset mode."""
        self._set_preset_item("kp", kp)
        self._set_preset_item("ki", ki)

        self.schedule_update_ha_state()

    def _set_preset_item(self, key: str, value: Any):
        """Set a preset item in the preset dictionary."""
        if self.preset_mode not in self._presets:
            self._presets[self.preset_mode] = {}
        self._presets[self.preset_mode][key] = value

    def _apply_preset(self, preset: dict[str, Any]):
        """Apply a preset to the climate entity."""
        if (temp := preset.get("temperature")) is not None:
            self._attr_target_temperature = float(temp)
        if (mode := preset.get("mode")) is not None:
            self._attr_hvac_mode = mode

        self.schedule_update_ha_state()
        self.zone.handle_preset_changed(preset)


class ZoneOutputSensor(SensorBase):  # pylint: disable=hass-enforce-class-module
    """Sensor to indicate the output value of the regulator."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 4
    _attr_icon = "mdi:gauge"

    def __init__(self, device_info: DeviceInfoModel) -> None:
        """Initialize the output sensor."""
        super().__init__("Output", device_info)


# TODO: Refactor in its own class like Window # pylint: disable=fixme
class ZoneTrvSensor(BinarySensorBase):  # pylint: disable=hass-enforce-class-module
    """Sensor to indicate TRV status in the zone."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = BinarySensorDeviceClass.HEAT

    def __init__(self, device_info: DeviceInfoModel) -> None:
        """Initialize the TRV sensor."""
        super().__init__("TRV", device_info)
