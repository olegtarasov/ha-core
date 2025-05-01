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
from homeassistant.helpers.selector import selector

from .const import (
    DOMAIN,
    STEP_CIRCUITS,
    STEP_ENTITIES,
    STEP_FINISH,
    STEP_MENU,
    STEP_USER,
    STEP_ZONES,
    SUBENTRY_TYPE_CIRCUIT,
    SUBENTRY_TYPE_ZONE,
)

_LOGGER = logging.getLogger(__name__)


class ExampleConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Example Integration."""

    VERSION = 1
    _input_data: dict[str, Any]
    _title: str

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step.

        Called when you initiate adding an integration via the UI
        """

        data_schema = vol.Schema(
            {vol.Required("main_thermostat_name", default="Main Thermostat"): str}
        )

        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                # Validate
                pass
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

            if "base" not in errors:
                await self.async_set_unique_id(user_input.get("main_thermostat_name"))
                self._abort_if_unique_id_configured()

                self._input_data = user_input
                self._title = user_input.get("main_thermostat_name")
                # return await self.async_step_menu()
                return self.async_create_entry(title=self._title, data=self._input_data)

        return self.async_show_form(step_id=STEP_USER, data_schema=data_schema)

    async def async_step_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show menu to configure entries."""
        menu_options = [STEP_CIRCUITS, STEP_ZONES, STEP_FINISH]

        return self.async_show_menu(step_id=STEP_MENU, menu_options=menu_options)

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

        data_schema = vol.Schema({vol.Required("zone_name"): str})

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
                self._title = user_input.get("zone_name")
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
                    "temperature_sensor", default=existing.get("temperature_sensor")
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
                    "window_sensors", default=existing.get("window_sensors", [])
                ): selector(
                    {
                        "entity": {
                            "filter": {
                                "domain": "binary_sensor",
                                "device_class": "door",
                            },
                            "multiple": True,
                        }
                    }
                ),
                vol.Optional("trvs", default=existing.get("trvs", [])): selector(
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

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
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
                    "temperature_sensor", default=existing.get("temperature_sensor")
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
                    "window_sensors", default=existing.get("window_sensors", [])
                ): selector(
                    {
                        "entity": {
                            "filter": {
                                "domain": "binary_sensor",
                                "device_class": "door",
                            },
                            "multiple": True,
                        }
                    }
                ),
                vol.Optional("trvs", default=existing.get("trvs", [])): selector(
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

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Reconfigures the zone."""
        return await self.async_step_entities(user_input)
