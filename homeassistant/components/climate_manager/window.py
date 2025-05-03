from datetime import datetime, timedelta

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.util import dt
from .common import BinarySensorBase, DeviceInfoModel, EntityBag
from .utils import get_state_bool


class ZoneWindow:
    def __init__(
        self,
        hass: HomeAssistant,
        window_sensors: list[str],
        device_info: DeviceInfoModel,
        entity_bag: EntityBag,
    ):
        self._window_sensors = window_sensors
        self._hass = hass

        # Entities
        self.window_entity = entity_bag.add_binary_sensor(ZoneWindowSensor(device_info))

        # State
        self._last_open = False
        self._warmup_time: datetime | None = None

    @property
    def window_open(self) -> bool:
        result = False
        for sensor in self._window_sensors:
            result = result or (get_state_bool(self._hass, sensor) or False)

        return result

    def should_heat(self) -> bool:
        """
        Decides whether regulator should be active based on whether window is open or closed
        :return: True if regulator needs to be active
        """
        window_open = self.window_open

        if self._last_open == window_open:  # There was no change
            if (
                not window_open
                and self._warmup_time is not None
                and dt.now() >= self._warmup_time
            ):
                # Window is closed and it stayed closed for warmup time after being open
                # We enable PID once again setting integral term to equal last output
                self._warmup_time = None

        else:  # Window state changed
            self._last_open = window_open

            if window_open:
                # If the window got opened, we stop the PID and reset warmup time
                self._warmup_time = None
            else:
                # If the window got closed, we calculate warmup time after which we should restart PID
                self._warmup_time = dt.now() + timedelta(minutes=5)

            self.window_entity.set_is_on(window_open)

        return not window_open and self._warmup_time is None


class ZoneWindowSensor(BinarySensorBase):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = BinarySensorDeviceClass.WINDOW

    def __init__(self, device_info: DeviceInfoModel):
        super().__init__("Window", device_info)
