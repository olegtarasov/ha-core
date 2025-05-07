"""Heating zone."""

import logging
from datetime import timedelta
from typing import Any, Awaitable, Callable, cast

from homeassistant.helpers.entity import Entity
from .online_tracker import OnlineTracker
from .window import ZoneWindow
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate import (
    HVACMode,
    PRESET_HOME,
)
from homeassistant.components.number import NumberEntity, NumberMode, RestoreNumber
from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from .common import (
    BinarySensorBase,
    ClimateBase,
    ControllerBase,
    DeviceInfoModel,
    HAEntityBase,
    NumberBase,
    SensorBase,
)
from .const import (
    CONFIG_REGULATOR_TYPE,
    CONFIG_TEMPERATURE_SENSOR,
    CONFIG_TRVS,
    CONFIG_WINDOW_SENSORS,
    REGULATOR_TYPE_PID,
)
from .regulator import HysteresisRegulator, PidRegulator, RegulatorBase
from .retry_tracker import RetryTracker
from .utils import SimpleAwaiter, get_state_bool, get_state_float

_LOGGER = logging.getLogger(__name__)


class Zone(ControllerBase):
    """Heating zone."""

    _regulator: RegulatorBase

    def __init__(self, hass: HomeAssistant, zone_config: ConfigSubentry) -> None:
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
        self._trvs = config_data[CONFIG_TRVS] if CONFIG_TRVS in config_data else []
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
        self._regulator.initialize(self.climate_entity.target_temperature)

    @property
    def current_temperature(self) -> float | None:
        return get_state_float(self._hass, self._temp_sensor)

    @property
    def target_temperature(self) -> float | None:
        return self.climate_entity.target_temperature

    @property
    def regulator_output(self) -> float:
        return self._regulator.output

    def control_temperature(self) -> None:
        try:
            cur_temp = self.current_temperature

            # If the sensor remains offline for longer than 5 sec, fault entity will be set
            self._sensor_online_tracker.is_online(cur_temp is not None)

            # If there is a fault or a window is open, we disable PID
            self._recalculate_regulator_enabled()
            if not self._regulator.enabled:
                return

            # The temp sensor can be temporarily offline, but we give it a chance to recover without pausing PID.
            if cur_temp is None:
                return

            self.climate_entity.set_current_temperature(cur_temp)

            self._regulator.calculate_output(cur_temp)
            output = self._regulator.output
            self.output_entity.set_native_value(output)

            # Operate TRVs
            if self._trvs:
                # If windows are open, save TRV batteries and do nothing
                if not self._window or self._window.should_heat():
                    self.operate_trvs(output)

            # If we reached here, we recovered from a previous unexpected fault. Clear the fault sensor and log
            if self.control_fault_entity.is_on:
                _LOGGER.info("Zone %s recovered from control fault", self._name)
                self.control_fault_entity.set_is_on(False)
        except Exception:
            # Function is called every second, and we don't want to spam the logs
            if not self.control_fault_entity.is_on:
                _LOGGER.error(
                    "Exception occured while trying to control heating in zone %s",
                    self._name,
                    exc_info=True,
                )
                self.control_fault_entity.set_is_on(True)

    def operate_trvs(self, output: float) -> None:
        mode = "heat" if output > 0 else "off"
        for trv in self._trvs:
            self._hass.services.call(
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
        result = True
        for enabler in self._regulator_enablers:
            result = result and enabler()

        self._regulator.enabled = result

    def _climate_enabled(self):
        return self.climate_entity.hvac_mode == HVACMode.HEAT

    def _no_sensor_fault(self):
        return not self.sensor_fault_entity.is_on

    def handle_target_temperature_changed(self, value: float) -> None:
        self._regulator.target_temperature = value

    def handle_preset_changed(self, preset: dict[str, Any]):
        # Climate entity applies its own preset values, we just need to handle other entities
        if isinstance(self._regulator, PidRegulator):
            pid = cast(PidRegulator, self._regulator)
            if (kp := preset.get("kp")) is not None:
                pid.kp = float(kp)
            if (ki := preset.get("ki")) is not None:
                pid.ki = float(ki)

    def _handle_pid_coeffs_changed(self):
        pid = cast(PidRegulator, self._regulator)
        self.climate_entity.save_pid_coeffs(pid.kp, pid.ki)


class ZoneControlFaultSensor(BinarySensorBase):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, device_info: DeviceInfoModel):
        super().__init__("Control Fault", device_info)


class ZoneSensorFaultSensor(BinarySensorBase):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, device_info: DeviceInfoModel):
        super().__init__("Sensor Fault", device_info)


class ZoneClimate(ClimateBase, RestoreEntity):
    _attr_target_temperature = 22
    _attr_min_temp = 18
    _attr_max_temp = 32

    def __init__(self, zone: Zone):
        super().__init__("Climate", zone.device_info)
        self.zone = zone

        self._presets: dict[str, dict[str, Any]] = {}

    async def async_added_to_hass(self) -> None:
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
        return {
            "presets": self._presets,
        }

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        self._attr_hvac_mode = hvac_mode
        self._set_preset_item("mode", str(self._attr_hvac_mode))
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs) -> None:
        if (temp := kwargs.get("temperature")) is not None:
            self._attr_target_temperature = float(temp)
            self._set_preset_item("temperature", self._attr_target_temperature)

            self.async_write_ha_state()
            self.zone.handle_target_temperature_changed(float(temp))

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        self._attr_preset_mode = preset_mode
        self.async_write_ha_state()

        if preset_mode in self._presets:
            self._apply_preset(self._presets[preset_mode])

    def save_pid_coeffs(self, kp: float, ki: float):
        self._set_preset_item("kp", kp)
        self._set_preset_item("ki", ki)

        self.schedule_update_ha_state()

    def _set_preset_item(self, key: str, value: Any):
        if self.preset_mode not in self._presets:
            self._presets[self.preset_mode] = {}
        self._presets[self.preset_mode][key] = value

    def _apply_preset(self, preset: dict[str, Any]):
        if (temp := preset.get("temperature")) is not None:
            self._attr_target_temperature = float(temp)
        if (mode := preset.get("mode")) is not None:
            self._attr_hvac_mode = mode

        self.schedule_update_ha_state()
        self.zone.handle_preset_changed(preset)


class ZoneOutputSensor(SensorBase):

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 4
    _attr_icon = "mdi:gauge"

    def __init__(self, device_info: DeviceInfoModel):
        super().__init__("Output", device_info)


# TODO: Refactor in its own class like Window
class ZoneTrvSensor(BinarySensorBase):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = BinarySensorDeviceClass.HEAT

    def __init__(self, device_info: DeviceInfoModel):
        super().__init__("TRV", device_info)
