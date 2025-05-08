from simple_pid import PID

from homeassistant.components.number import NumberMode
from homeassistant.const import EntityCategory
from .common import DeviceInfoModel, EntityBag, NumberBase, SensorBase
from .event_hook import EventHook


class RegulatorBase:
    """Base class for temperature regulators."""

    def initialize(self, target_temperature: float) -> None:
        """Initialize the regulator with the target temperature."""
        raise NotImplementedError

    def calculate_output(self, cur_temp: float):
        """Calculate the output based on the current temperature."""
        raise NotImplementedError

    @property
    def output(self) -> float:
        """Get the current output of the regulator."""
        raise NotImplementedError

    @property
    def enabled(self) -> bool:
        """Get whether the regulator is enabled."""
        raise NotImplementedError

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Set whether the regulator is enabled."""
        raise NotImplementedError

    @property
    def target_temperature(self) -> float:
        """Get the target temperature of the regulator."""
        raise NotImplementedError

    @target_temperature.setter
    def target_temperature(self, value: float) -> None:
        """Set the target temperature of the regulator."""
        raise NotImplementedError


class PidRegulator(RegulatorBase):

    _pid: PID

    def __init__(
        self,
        entity_bag: EntityBag,
        device_info: DeviceInfoModel,
        average_samples: int = 20,
    ):
        # Events
        self.on_coeffs_changed = EventHook()

        # Entities
        self.kp_entity = entity_bag.add_number(PidKpNumber(self, device_info))
        self.ki_entity = entity_bag.add_number(PidKiNumber(self, device_info))
        self.proportional_entity = entity_bag.add_sensor(
            PidProportionalSensor(device_info)
        )
        self.integral_entity = entity_bag.add_sensor(PidIntegralSensor(device_info))

        # Private
        self._average_samples = average_samples
        self._output: list[float] = []

    def initialize(self, target_temperature: float) -> None:
        """Initialize the PID regulator with the target temperature."""
        self._pid = PID(
            self.kp_entity.native_value,
            self.ki_entity.native_value,
            0,
            target_temperature,
            1,
            (-1, 1),
        )

    @property
    def kp(self) -> float:
        """Get the proportional coefficient of the PID regulator."""
        return self._pid.Kp

    @kp.setter
    def kp(self, value: float) -> None:
        """Set the proportional coefficient of the PID regulator."""
        self._pid.Kp = value
        self.kp_entity.set_native_value_no_notify(value)

    @property
    def ki(self) -> float:
        """Get the integral coefficient of the PID regulator."""
        return self._pid.Ki

    @ki.setter
    def ki(self, value: float) -> None:
        """Set the integral coefficient of the PID regulator."""
        self._pid.Ki = value
        self.ki_entity.set_native_value_no_notify(value)

    @property
    def enabled(self) -> bool:
        """Get whether the PID regulator is enabled."""
        return self._pid.auto_mode

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Set whether the PID regulator is enabled."""
        if self._pid.auto_mode == value:
            return

        if value:
            self._pid.auto_mode = True
        else:
            self._pid.auto_mode = False
            self._output.clear()

    @property
    def target_temperature(self) -> float:
        """Get the target temperature of the PID regulator."""
        return self._pid.setpoint

    @target_temperature.setter
    def target_temperature(self, value: float) -> None:
        """Set the target temperature of the PID regulator."""
        self._pid.setpoint = value

    def calculate_output(self, cur_temp: float):
        """Calculate the output of the PID regulator based on the current temperature."""
        if not self.enabled:
            return

        self._output.append(self._pid(cur_temp))
        if len(self._output) > self._average_samples:
            self._output.pop(0)

        self.proportional_entity.set_native_value(self._pid.components[0])
        self.integral_entity.set_native_value(self._pid.components[1])

    @property
    def output(self) -> float:
        """Get the average output of the PID regulator."""
        if not self._pid.auto_mode or len(self._output) == 0:
            return 0

        return sum(self._output) / len(self._output)

    def handle_coeffs_changed(self):
        """Handle changes in the PID coefficients."""
        self._pid.Kp = self.kp_entity.native_value
        self._pid.Ki = self.ki_entity.native_value
        self.on_coeffs_changed()


class HysteresisRegulator(RegulatorBase):

    _target: float

    def __init__(self):
        self._enabled = True
        self._output = 0

    def initialize(self, target_temperature: float) -> None:
        """Initialize the hysteresis regulator with the target temperature."""
        self._target = target_temperature

    def calculate_output(self, cur_temp: float):
        """Calculate the output of the hysteresis regulator based on the current temperature."""
        if not self.enabled:
            return

        if cur_temp <= self._target - 1:
            self._output = 0.05
        elif cur_temp >= self._target + 1:
            self._output = 0

    @property
    def output(self) -> float:
        """Get the output of the hysteresis regulator."""
        return self._output

    @property
    def enabled(self) -> bool:
        """Get whether the hysteresis regulator is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Set whether the hysteresis regulator is enabled."""
        self._enabled = value

    @property
    def target_temperature(self) -> float:
        """Get the target temperature of the hysteresis regulator."""
        return self._target

    @target_temperature.setter
    def target_temperature(self, value: float) -> None:
        """Set the target temperature of the hysteresis regulator."""
        self._target = value


class PidNumberBase(NumberBase):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = 0
    _attr_native_max_value = 100000
    _attr_native_step = 0.001
    _attr_mode = NumberMode.BOX

    def __init__(
        self, name: str, regulator: PidRegulator, device_info: DeviceInfoModel
    ):
        """Initialize a PID number base entity."""
        super().__init__(name, device_info)

        self._regulator = regulator

    def set_native_value(self, value: float) -> None:
        """Set the native value of the PID number entity and notify the regulator."""
        super().set_native_value(value)
        self._regulator.handle_coeffs_changed()

    def set_native_value_no_notify(self, value: float) -> None:
        """Set the native value of the PID number entity without notifying the regulator."""
        super().set_native_value(value)


class PidKpNumber(PidNumberBase):
    _attr_native_value = 0.5

    def __init__(self, regulator: PidRegulator, device_info: DeviceInfoModel):
        """Initialize a Kp PID number entity."""
        super().__init__("Kp", regulator, device_info)


class PidKiNumber(PidNumberBase):
    _attr_native_value = 0.001

    def __init__(self, regulator: PidRegulator, device_info: DeviceInfoModel):
        """Initialize a Ki PID number entity."""
        super().__init__("Ki", regulator, device_info)


class PidProportionalSensor(SensorBase):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 4
    _attr_icon = "mdi:gauge"

    def __init__(self, device_info: DeviceInfoModel):
        """Initialize a PID proportional sensor entity."""
        super().__init__("PID Proportional", device_info)


class PidIntegralSensor(SensorBase):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 4
    _attr_icon = "mdi:gauge"

    def __init__(self, device_info: DeviceInfoModel):
        """Initialize a PID integral sensor entity."""
        super().__init__("PID Integral", device_info)
