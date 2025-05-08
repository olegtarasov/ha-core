"""Window tracker."""

from datetime import datetime, timedelta

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from .common import BinarySensorBase, DeviceInfoModel, EntityBag
from .utils import get_state_bool


class ZoneWindow:
    """Zone window."""

    def __init__(
        self,
        hass: HomeAssistant,
        window_sensors: list[str],
        device_info: DeviceInfoModel,
        entity_bag: EntityBag,
    ) -> None:
        """Initialize the ZoneWindow with the specified parameters."""
        self._window_sensors = window_sensors
        self._hass = hass

        # Entities
        self.window_entity = entity_bag.add_binary_sensor(ZoneWindowSensor(device_info))

        # State
        self._last_open = False
        self._warmup_time: datetime | None = None

    @property
    def window_open(self) -> bool:
        """Determine if any of the window sensors indicate the window is open."""
        result = False
        for sensor in self._window_sensors:
            result = result or (get_state_bool(self._hass, sensor) or False)

        return result

    def should_heat(self) -> bool:
        """Determine if the regulator should be active based on the window state."""
        window_open = self.window_open

        if self._last_open == window_open:  # There was no change
            if (
                not window_open
                and self._warmup_time is not None
                and dt_util.now() >= self._warmup_time
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
                self._warmup_time = dt_util.now() + timedelta(minutes=5)

            self.window_entity.set_is_on(window_open)

        return not window_open and self._warmup_time is None


class ZoneWindowSensor(BinarySensorBase):  # pylint: disable=hass-enforce-class-module
    """Zone window sensor."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = BinarySensorDeviceClass.WINDOW

    def __init__(self, device_info: DeviceInfoModel) -> None:
        """Initialize the ZoneWindowSensor with the provided device information."""
        super().__init__("Window", device_info)
