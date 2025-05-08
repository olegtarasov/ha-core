"""Hub."""

from datetime import datetime, timedelta
import logging

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.config_entries import ConfigEntry, ConfigSubentry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_track_time_interval

from .circuit import Circuit
from .common import BinarySensorBase, ControllerBase, DeviceInfoModel, SensorBase
from .const import CONFIG_BOILER_STATUS_SENSOR, CONFIG_ZONES
from .online_tracker import OnlineTracker
from .utils import get_state_bool
from .zone import Zone

_LOGGER = logging.getLogger(__name__)


class Hub(ControllerBase):
    """Main thermostat hub class."""

    def __init__(
        self,
        hass: HomeAssistant,
        hub_config: ConfigEntry,
        zones_config: list[ConfigSubentry],
        circuits_config: list[ConfigSubentry],
    ) -> None:
        """Initialize the hub."""
        super().__init__(hass, hub_config.title)

        # Device
        self.device_info = DeviceInfoModel(
            self._name, self._unique_id, "Main Thermostat"
        )

        # Config
        config_data = hub_config.data.copy()
        self.boiler_online_sensor: str | None = config_data.get(
            CONFIG_BOILER_STATUS_SENSOR
        )
        self.zones = {
            zone_config.subentry_id: Zone(hass, zone_config)
            for zone_config in zones_config
        }
        # self.zone_circuit_id_map: dict[str, str] = {}

        circuit_zone_map: dict[str, list[str]] = {}

        device_registry = dr.async_get(hass)
        for circuit_config in circuits_config:
            devices = circuit_config.data[CONFIG_ZONES]
            circuit_zone_map[circuit_config.subentry_id] = []
            for device in devices:
                device = device_registry.async_get(device)
                # Maybe zone was deleted but is still referenced in circuit
                if not device:
                    continue
                subentry_id = next(
                    iter(next(iter(device.config_entries_subentries.values())))
                )
                circuit_zone_map[circuit_config.subentry_id].append(subentry_id)

        self.circuits = {
            circuit_config.subentry_id: Circuit(
                hass,
                circuit_config,
                [
                    self.zones[zone_id]
                    for zone_id in circuit_zone_map[circuit_config.subentry_id]
                ],
            )
            for circuit_config in circuits_config
        }

        # Entities
        self.output_entity = self.entity_bag.add_sensor(HubOutput(self.device_info))
        self.control_fault_entity = self.entity_bag.add_binary_sensor(
            HubControlFaultSensor(self.device_info)
        )
        self.boiler_fault_entity = (
            self.entity_bag.add_binary_sensor(HubBoilerFaultSensor(self.device_info))
            if self.boiler_online_sensor
            else None
        )

        # Private
        self._unsubscribe = None
        self._boiler_online_tracker = OnlineTracker(
            self.boiler_fault_entity,
            timedelta(seconds=20),
            "Boiler",
            self._open_trvs_start_pumps,
        )

    def initialize(self):
        """Initialize the hub components."""
        for zone in self.zones.values():
            zone.initialize()

        self._unsubscribe = async_track_time_interval(
            self._hass, self._async_control_heating, timedelta(seconds=1)
        )

    def destroy(self):
        """Destroy the hub and clean up resources."""
        if self._unsubscribe:
            self._unsubscribe()

    async def _async_control_heating(self, _now: datetime) -> None:
        """Control the heating system based on current conditions."""
        # If sensor is not set, we assume the boiler is online
        if self.boiler_online_sensor:
            boiler_online = get_state_bool(
                self._hass, self.boiler_online_sensor, default=False
            )
            if not await self._boiler_online_tracker.is_online(boiler_online):
                return

        try:
            output = 0.0

            for zone in self.zones.values():
                await zone.control_temperature()
                output = max(output, zone.regulator_output)

            for circuit in self.circuits.values():
                await circuit.control_circuit()

            self.output_entity.set_native_value(output)

            # If we reached here, we recovered from a previous unexpected fault. Clear the fault sensor and log
            if self.control_fault_entity.is_on:
                _LOGGER.info("Hub %s recovered from unexpected fault", self._name)
                self.control_fault_entity.set_is_on(False)
        except Exception:
            # Function is called every second, and we don't want to spam the logs
            if not self.control_fault_entity.is_on:
                _LOGGER.exception(
                    "Exception occured while trying to control heating in hub %s",
                    self._name,
                )
                self.control_fault_entity.set_is_on(True)

    async def _open_trvs_start_pumps(self):
        """Start pumps and open TRVs to circulate heating."""
        _LOGGER.info("Starting pumps and opening TRVs")
        for zone in self.zones.values():
            await zone.operate_trvs(1)
        for circuit in self.circuits.values():
            await circuit.set_active(True)


class HubControlFaultSensor(
    BinarySensorBase
):  # pylint: disable=hass-enforce-class-module
    """Binary sensor indicating control fault in the hub."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, device_info: DeviceInfoModel) -> None:
        """Initialize the control fault sensor."""
        super().__init__("Control Fault", device_info)


class HubBoilerFaultSensor(
    BinarySensorBase
):  # pylint: disable=hass-enforce-class-module
    """Binary sensor indicating boiler fault in the hub."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    def __init__(self, device_info: DeviceInfoModel) -> None:
        """Initialize the boiler fault sensor."""
        super().__init__("Boiler Fault", device_info)


class HubOutput(SensorBase):  # pylint: disable=hass-enforce-class-module
    """Hub output sensor."""

    _attr_suggested_display_precision = 4
    _attr_icon = "mdi:gauge"

    def __init__(self, device_info: DeviceInfoModel) -> None:
        """Initialize the output sensor."""
        super().__init__("Output", device_info)
