from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.util import slugify

from .const import DOMAIN
from .hub import Hub
from .zone import Zone


class ClimateEntityBase:
    def __init__(self, name: str):
        self.name = name
        self.unique_id = slugify(name)

class ClimateDeviceInfo:
    def __init__(self, name: str, identifier: str, model: str):
        self.model = model
        self.identifier = identifier
        self.name = name

    def get_device_info(self) -> DeviceInfo:
        return DeviceInfo(
            name=self.name,
            identifiers={(DOMAIN, self.identifier)},
            manufacturer="Cats Ltd.",
            model=self.model
        )

class BinarySensorBase(BinarySensorEntity):
    _attr_should_poll = False

    def __init__(self, name: str, device_info: ClimateDeviceInfo):
        self._attr_name = name
        self._attr_unique_id = slugify(f"{device_info.name} {name}")
        self._device_info = device_info

    def device_info(self) -> DeviceInfo | None:
        return self._device_info.get_device_info()


class HubBinarySensorBase(BinarySensorBase):
    def __init__(self, name: str, hub: Hub):
        super().__init__(name, hub.device_info)


class ZoneBinarySensorBase(BinarySensorBase):
    def __init__(self, name: str, zone: Zone):
        super().__init__(name, zone.device_info)
