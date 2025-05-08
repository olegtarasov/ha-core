"""Common entities and base classes."""

from __future__ import annotations

from typing import TypeVar

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.climate import (
    PRESET_AWAY,
    PRESET_HOME,
    PRESET_SLEEP,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.components.number import RestoreNumber
from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.util import slugify

from .const import DOMAIN


class ControllerBase:
    """Base class for controllers, providing common initialization and an entity bag for managing entities."""

    def __init__(self, hass: HomeAssistant, name: str) -> None:
        """Initialize base controller."""
        self._hass = hass
        self._name = name
        self._unique_id = slugify(name)

        self.entity_bag = EntityBag()


class DeviceInfoModel:
    """Model for storing device information and providing a DeviceInfo object."""

    def __init__(self, name: str, identifier: str, model: str) -> None:
        """Intialize."""
        self.model = model
        self.identifier = identifier
        self.name = name

    def get_device_info(self) -> DeviceInfo:
        """Return the DeviceInfo object for the device."""
        return DeviceInfo(
            name=self.name,
            identifiers={(DOMAIN, self.identifier)},
            manufacturer="Cats Ltd.",
            model=self.model,
        )


class HAEntityBase(Entity):  # pylint: disable=hass-enforce-class-module
    """Base class for HA entities, providing common attributes and initialization."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, name: str, device_info: DeviceInfoModel) -> None:
        """Intialize."""
        self._attr_name = name
        self._attr_unique_id = f"{DOMAIN}_{slugify(f'{device_info.name} {name}')}"
        self._device_info = device_info

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return the device information."""
        return self._device_info.get_device_info()


class SensorBase(HAEntityBase, SensorEntity):  # pylint: disable=hass-enforce-class-module
    """Base class for sensor entities, providing common attributes and functionality."""

    _attr_state_class = SensorStateClass.MEASUREMENT

    def set_native_value(self, value: float) -> None:
        """Update the native value of the sensor."""
        self._attr_native_value = value
        self.schedule_update_ha_state()


class BinarySensorBase(HAEntityBase, BinarySensorEntity):  # pylint: disable=hass-enforce-class-module
    """Base class for binary sensor entities, providing common attributes and functionality."""

    _attr_is_on = False

    def set_is_on(self, value: bool) -> None:
        """Update the on/off state of the binary sensor."""
        self._attr_is_on = value
        self.schedule_update_ha_state()


class NumberBase(HAEntityBase, RestoreNumber):  # pylint: disable=hass-enforce-class-module
    """Base class for number entities, providing common attributes and functionality."""

    async def async_added_to_hass(self) -> None:
        """Initialize the number entity, restoring last known value if available."""
        if (last := await self.async_get_last_number_data()) is not None:
            if last.native_value is not None:
                self._attr_native_value = last.native_value

    def set_native_value(self, value: float) -> None:
        """Update the current value of the number entity."""
        self._attr_native_value = value
        self.schedule_update_ha_state()


class ClimateBase(HAEntityBase, ClimateEntity):  # pylint: disable=hass-enforce-class-module
    """Base class for climate entities, providing common attributes and functionality."""

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

    def set_current_temperature(self, value: float) -> None:
        """Update the current temperature of the climate entity."""
        self._attr_current_temperature = value
        self.schedule_update_ha_state()


class EntityBag:
    """Container for managing lists of entities of different types."""

    def __init__(self) -> None:
        """Intialize."""
        self.binary_sensors: list[Entity] = []
        self.sensors: list[Entity] = []
        self.climates: list[Entity] = []
        self.numbers: list[Entity] = []

    TBinarySensorEntity = TypeVar("TBinarySensorEntity", bound=BinarySensorBase)
    TSensorEntity = TypeVar("TSensorEntity", bound=SensorBase)
    TClimateEntity = TypeVar("TClimateEntity", bound=ClimateBase)
    TNumberEntity = TypeVar("TNumberEntity", bound=NumberBase)

    def add_binary_sensor(self, sensor: TBinarySensorEntity) -> TBinarySensorEntity:
        """Add a binary sensor to the list."""
        self.binary_sensors.append(sensor)
        return sensor

    def add_sensor(self, sensor: TSensorEntity) -> TSensorEntity:
        """Add a sensor to the list."""
        self.sensors.append(sensor)
        return sensor

    def add_climate(self, climate: TClimateEntity) -> TClimateEntity:
        """Add a climate entity to the list."""
        self.climates.append(climate)
        return climate

    def add_number(self, number: TNumberEntity) -> TNumberEntity:
        """Add a number entity to the list."""
        self.numbers.append(number)
        return number
