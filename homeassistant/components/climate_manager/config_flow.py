"""Config flow for CLimate Manager."""

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.core import callback
from homeassistant.helpers.entity import async_generate_entity_id
from homeassistant.helpers.selector import selector

from .const import (
    CONFIG_BOILER_STATUS_SENSOR,
    CONFIG_MAIN_THERMOSTAT_NAME,
    CONFIG_REGULATOR_TYPE,
    CONFIG_SWITCHES,
    CONFIG_TEMPERATURE_SENSOR,
    CONFIG_TRVS,
    CONFIG_WINDOW_SENSORS,
    CONFIG_ZONE_NAME,
    CONFIG_ZONES,
    DOMAIN,
    ENTITY_ID_FORMAT,
    REGULATOR_TYPE_HYSTERESIS,
    REGULATOR_TYPE_PID,
    STEP_BOILER,
    STEP_ENTITIES,
    STEP_USER,
    SUBENTRY_TYPE_CIRCUIT,
    SUBENTRY_TYPE_ZONE,
)

_LOGGER = logging.getLogger(__name__)


class HubConfigFlow(ConfigFlow, domain=DOMAIN):
    """Hub config flow."""

    VERSION = 1
    _title: str

    def __init__(self) -> None:
        """Init hub config flow."""
        self._input_data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """First step in user-initiated flow."""
        data_schema = vol.Schema(
            {vol.Required(CONFIG_MAIN_THERMOSTAT_NAME, default="Main Thermostat"): str}
        )

        if user_input is not None:
            self._input_data = user_input
            self._title = user_input.get(CONFIG_MAIN_THERMOSTAT_NAME)
            unique_id = async_generate_entity_id(
                ENTITY_ID_FORMAT,
                self._title,
                hass=self.hass,
            )

            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            return await self.async_step_boiler()

        return self.async_show_form(step_id=STEP_USER, data_schema=data_schema)

    async def async_step_boiler(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure boiler online sensor."""
        existing = {}
        if self.source == SOURCE_RECONFIGURE:
            existing = self._get_reconfigure_entry().data.copy()

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONFIG_BOILER_STATUS_SENSOR,
                    default=existing.get(CONFIG_BOILER_STATUS_SENSOR),
                ): selector(
                    {
                        "entity": {
                            "filter": {
                                "domain": "binary_sensor",
                            }
                        }
                    }
                ),
            }
        )

        if user_input is not None:
            self._input_data.update(user_input)
            if self.source == SOURCE_RECONFIGURE:
                return self.async_update_reload_and_abort(
                    self._get_reconfigure_entry(), data_updates=self._input_data
                )

            return self.async_create_entry(title=self._title, data=self._input_data)

        return self.async_show_form(step_id=STEP_BOILER, data_schema=data_schema)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Reconfigure step."""
        return await self.async_step_boiler()

    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return subentries supported by this integration."""
        return {
            SUBENTRY_TYPE_ZONE: ZoneSubentryFlowHandler,
            SUBENTRY_TYPE_CIRCUIT: CircuitSubentryFlowHandler,
        }


class ZoneSubentryFlowHandler(ConfigSubentryFlow):
    """Handle subentry flow for adding and modifying a heating zone."""

    VERSION = 1
    _input_data: dict[str, Any]
    _title: str

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """User flow to add a new heating zone."""

        data_schema = vol.Schema({vol.Required(CONFIG_ZONE_NAME): str})

        errors: dict[str, str] = {}

        if user_input is not None:
            # The form has been filled in and submitted, so process the data provided.
            try:
                pass
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

            if "base" not in errors:
                self._input_data = user_input
                self._title = user_input.get(CONFIG_ZONE_NAME)
                return await self.async_step_entities()

        return self.async_show_form(step_id=STEP_USER, data_schema=data_schema)

    async def async_step_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Entities flow to configure heating zone entities."""

        # Try to load existing values
        existing = {}
        if self.source == SOURCE_RECONFIGURE:
            existing = self._get_reconfigure_subentry().data.copy()

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONFIG_REGULATOR_TYPE,
                    default=existing.get(CONFIG_REGULATOR_TYPE, REGULATOR_TYPE_PID),
                ): selector(
                    {
                        "select": {
                            "options": [REGULATOR_TYPE_PID, REGULATOR_TYPE_HYSTERESIS]
                        }
                    }
                ),
                vol.Required(
                    CONFIG_TEMPERATURE_SENSOR,
                    default=existing.get(CONFIG_TEMPERATURE_SENSOR),
                ): selector(
                    {
                        "entity": {
                            "filter": {
                                "domain": "sensor",
                                "device_class": "temperature",
                            }
                        }
                    }
                ),
                vol.Optional(
                    CONFIG_WINDOW_SENSORS,
                    default=existing.get(CONFIG_WINDOW_SENSORS, []),
                ): selector(
                    {
                        "entity": {
                            "filter": {
                                "domain": "binary_sensor",
                                # "device_class": "door",
                            },
                            "multiple": True,
                        }
                    }
                ),
                vol.Optional(
                    CONFIG_TRVS, default=existing.get(CONFIG_TRVS, [])
                ): selector(
                    {
                        "entity": {
                            "filter": {"domain": "climate"},
                            "multiple": True,
                        }
                    }
                ),
            }
        )

        errors: dict[str, str] = {}

        if user_input is not None:
            # The form has been filled in and submitted, so process the data provided.
            try:
                pass
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

            if "base" not in errors:
                self._input_data = user_input

                if self.source == SOURCE_RECONFIGURE:
                    return self.async_update_and_abort(
                        self._get_entry(),
                        self._get_reconfigure_subentry(),
                        data_updates=self._input_data,
                    )

                return self.async_create_entry(title=self._title, data=self._input_data)

        return self.async_show_form(step_id=STEP_ENTITIES, data_schema=data_schema)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Reconfigures the zone."""
        return await self.async_step_entities(user_input)


class CircuitSubentryFlowHandler(ConfigSubentryFlow):
    """Handle subentry flow for adding and modifying a heating circuit."""

    VERSION = 1
    _input_data: dict[str, Any]
    _title: str

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """User flow to add a new heating circuit."""

        data_schema = vol.Schema({vol.Required("circuit_name"): str})

        errors: dict[str, str] = {}

        if user_input is not None:
            # The form has been filled in and submitted, so process the data provided.
            try:
                pass
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

            if "base" not in errors:
                self._input_data = user_input
                self._title = user_input.get("circuit_name")
                return await self.async_step_entities()

        return self.async_show_form(step_id=STEP_USER, data_schema=data_schema)

    async def async_step_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Entities flow to configure heating circuit entities."""

        # Try to load existing values
        existing = {}
        if self.source == SOURCE_RECONFIGURE:
            existing = self._get_reconfigure_subentry().data.copy()

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONFIG_ZONES, default=existing.get(CONFIG_ZONES, [])
                ): selector(
                    {
                        "device": {
                            "filter": {
                                "integration": DOMAIN,
                                "model": "Zone Thermostat",
                            },
                            "multiple": True,
                        }
                    }
                ),
                vol.Optional(
                    CONFIG_SWITCHES, default=existing.get(CONFIG_SWITCHES, [])
                ): selector(
                    {
                        "entity": {
                            "filter": {"domain": "switch"},
                            "multiple": True,
                        }
                    }
                ),
            }
        )

        errors: dict[str, str] = {}

        if user_input is not None:
            # The form has been filled in and submitted, so process the data provided.
            try:
                pass
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

            if "base" not in errors:
                self._input_data = user_input

                if self.source == SOURCE_RECONFIGURE:
                    return self.async_update_and_abort(
                        self._get_entry(),
                        self._get_reconfigure_subentry(),
                        data_updates=self._input_data,
                    )

                return self.async_create_entry(title=self._title, data=self._input_data)

        return self.async_show_form(step_id=STEP_ENTITIES, data_schema=data_schema)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Reconfigures the zone."""
        return await self.async_step_entities(user_input)
