from simple_pid import PID

from homeassistant.components.number import NumberMode
from homeassistant.const import EntityCategory
from .common import DeviceInfoModel, EntityBag, NumberBase, SensorBase
from .event_hook import EventHook


class RegulatorBase:
    def initialize(self, target_temperature: float) -> None:
        raise NotImplementedError

    def calculate_output(self, cur_temp: float):
        raise NotImplementedError

    @property
    def output(self) -> float:
        raise NotImplementedError

    @property
    def enabled(self) -> bool:
        raise NotImplementedError

    @enabled.setter
    def enabled(self, value: bool) -> None:
        raise NotImplementedError

    @property
    def target_temperature(self) -> float:
        raise NotImplementedError

    @target_temperature.setter
    def target_temperature(self, value: float) -> None:
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
        return self._pid.Kp

    @kp.setter
    def kp(self, value: float) -> None:
        self._pid.Kp = value
        self.kp_entity.set_native_value_no_notify(value)

    @property
    def ki(self) -> float:
        return self._pid.Ki

    @ki.setter
    def ki(self, value: float) -> None:
        self._pid.Ki = value
        self.ki_entity.set_native_value_no_notify(value)

    @property
    def enabled(self) -> bool:
        return self._pid.auto_mode

    @enabled.setter
    def enabled(self, value: bool) -> None:
        if self._pid.auto_mode == value:
            return

        if value:
            self._pid.auto_mode = True
        else:
            self._pid.auto_mode = False
            self._output.clear()

    @property
    def target_temperature(self) -> float:
        return self._pid.setpoint

    @target_temperature.setter
    def target_temperature(self, value: float) -> None:
        self._pid.setpoint = value

    def calculate_output(self, cur_temp: float):
        if not self.enabled:
            return

        self._output.append(self._pid(cur_temp))
        if len(self._output) > self._average_samples:
            self._output.pop(0)

        self.proportional_entity.set_native_value(self._pid.components[0])
        self.integral_entity.set_native_value(self._pid.components[1])

    @property
    def output(self) -> float:
        if not self._pid.auto_mode or len(self._output) == 0:
            return 0

        return sum(self._output) / len(self._output)

    def handle_coeffs_changed(self):
        self._pid.Kp = self.kp_entity.native_value
        self._pid.Ki = self.ki_entity.native_value
        self.on_coeffs_changed()


class HysteresisRegulator(RegulatorBase):

    _target: float

    def __init__(self):
        self._enabled = True
        self._output = 0

    def initialize(self, target_temperature: float) -> None:
        self._target = target_temperature

    def calculate_output(self, cur_temp: float):
        if not self.enabled:
            return

        if cur_temp <= self._target - 1:
            self._output = 0.05
        elif cur_temp >= self._target + 1:
            self._output = 0

    @property
    def output(self) -> float:
        return self._output

    @property
    def enabled(self) -> bool:
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self._enabled = value

    @property
    def target_temperature(self) -> float:
        return self._target

    @target_temperature.setter
    def target_temperature(self, value: float) -> None:
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
        super().__init__(name, device_info)

        self._regulator = regulator

    def set_native_value(self, value: float) -> None:
        super().set_native_value(value)
        self._regulator.handle_coeffs_changed()

    def set_native_value_no_notify(self, value: float) -> None:
        super().set_native_value(value)


class PidKpNumber(PidNumberBase):
    _attr_native_value = 0.5

    def __init__(self, regulator: PidRegulator, device_info: DeviceInfoModel):
        super().__init__("Kp", regulator, device_info)


class PidKiNumber(PidNumberBase):
    _attr_native_value = 0.001

    def __init__(self, regulator: PidRegulator, device_info: DeviceInfoModel):
        super().__init__("Ki", regulator, device_info)


class PidProportionalSensor(SensorBase):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 4
    _attr_icon = "mdi:gauge"

    def __init__(self, device_info: DeviceInfoModel):
        super().__init__("PID Proportional", device_info)


class PidIntegralSensor(SensorBase):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_suggested_display_precision = 4
    _attr_icon = "mdi:gauge"

    def __init__(self, device_info: DeviceInfoModel):
        super().__init__("PID Integral", device_info)
