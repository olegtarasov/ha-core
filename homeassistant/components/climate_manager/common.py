from __future__ import annotations

from homeassistant.helpers.entity import Entity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.util import slugify
from homeassistant.components.climate import ClimateEntity
from homeassistant.components.climate import (
    ClimateEntityFeature,
    HVACMode,
    PRESET_HOME,
    PRESET_SLEEP,
    PRESET_AWAY,
)
from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTemperature

from .const import DOMAIN
from homeassistant.components.number import RestoreNumber


class EntityBag:
    def __init__(self):
        self.binary_sensors: list[Entity] = []
        self.sensors: list[Entity] = []
        self.climates: list[Entity] = []
        self.numbers: list[Entity] = []

    def add_binary_sensor(self, sensor: BinarySensorBase) -> BinarySensorBase:
        self.binary_sensors.append(sensor)
        return sensor

    def add_sensor(self, sensor: SensorBase) -> SensorBase:
        self.sensors.append(sensor)
        return sensor

    def add_climate(self, climate: ClimateEntityBase) -> ClimateEntityBase:
        self.climates.append(climate)
        return climate

    def add_number(self, number: NumberBase) -> NumberBase:
        self.numbers.append(number)
        return number


class ControllerBase:
    def __init__(self, hass: HomeAssistant, name: str):
        self._hass = hass
        self._name = name
        self._unique_id = slugify(name)

        self.entity_bag = EntityBag()


class DeviceInfoModel:
    def __init__(self, name: str, identifier: str, model: str):
        self.model = model
        self.identifier = identifier
        self.name = name

    def get_device_info(self) -> DeviceInfo:
        return DeviceInfo(
            name=self.name,
            identifiers={(DOMAIN, self.identifier)},
            manufacturer="Cats Ltd.",
            model=self.model,
        )


class HAEntityBase(Entity):
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, name: str, device_info: DeviceInfoModel):
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{slugify(f"{device_info.name} {name}")}"
        self._device_info = device_info

    @property
    def device_info(self) -> DeviceInfo | None:
        return self._device_info.get_device_info()


class SensorBase(HAEntityBase, SensorEntity):

    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, name: str, device_info: DeviceInfoModel):
        super().__init__(name, device_info)

    async def async_set_native_value(self, value: float) -> None:
        self._attr_native_value = value
        self.async_write_ha_state()


class BinarySensorBase(HAEntityBase, BinarySensorEntity):

    _attr_is_on = False

    def __init__(self, name: str, device_info: DeviceInfoModel):
        super().__init__(name, device_info)

    async def async_set_is_on(self, value: bool) -> None:
        self._attr_is_on = value
        self.async_write_ha_state()


class NumberBase(HAEntityBase, RestoreNumber):
    def __init__(self, name: str, device_info: DeviceInfoModel):
        super().__init__(name, device_info)

    async def async_added_to_hass(self) -> None:
        if (last := await self.async_get_last_number_data()) is not None:
            if last.native_value is not None:
                self._attr_native_value = last.native_value

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self._attr_native_value = value
        self.async_write_ha_state()


class ClimateEntityBase(HAEntityBase, ClimateEntity):
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_hvac_mode = HVACMode.HEAT
    _attr_preset_modes = [PRESET_HOME, PRESET_SLEEP, PRESET_AWAY]
    _attr_preset_mode = PRESET_HOME
    _attr_precision = 0.1
    _attr_target_temperature_step = 0.5
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, name: str, device_info: DeviceInfoModel):
        super().__init__(name, device_info)


class FaultSensor(BinarySensorBase):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, device_info: DeviceInfoModel):
        super().__init__("Fault", device_info)
