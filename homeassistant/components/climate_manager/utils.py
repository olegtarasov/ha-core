import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.util import dt

_LOGGER = logging.getLogger(__name__)

bool_true = {"y", "yes", "true", "on"}
bool_false = {"n", "no", "false", "off"}


class SimpleAwaiter:
    def __init__(self, wait_time: timedelta) -> None:
        start_time = dt.now()
        self.target_time = start_time + wait_time

    @property
    def elapsed(self) -> bool:
        return dt.now() >= self.target_time


def str_to_bool(value: str) -> bool | None:
    if value in bool_true:
        return True
    elif value in bool_false:
        return False
    else:
        return None


def get_state_value(
    hass: HomeAssistant,
    entity: str,
    attribute: str | None = None,
    default: Any = None,
) -> str | None:
    state = hass.states.get(entity)
    if state is None:
        return default

    value: str
    if attribute is not None:
        if attribute in state.attributes:
            return state.attributes[attribute]
        return default

    return state.state


def get_state_bool(
    hass: HomeAssistant,
    entity: str,
    attribute: str | None = None,
    default: Any = None,
) -> bool | None:
    value = get_state_value(hass, entity, attribute, default)

    try:
        return str_to_bool(value.lower())
    except:
        _LOGGER.warning(
            "Failed to get bool state for entity %s%s. Received: %s",
            entity,
            f".{attribute}" if attribute is not None else "",
            value,
        )
        return None


def get_state_float(
    hass: HomeAssistant,
    entity: str,
    attribute: str | None = None,
    default: Any = None,
) -> float | None:
    value = get_state_value(hass, entity, attribute, default)

    try:
        return float(value)
    except:
        _LOGGER.warning(
            "Failed to get floar state for entity %s%s. Received: %s",
            entity,
            f".{attribute}" if attribute is not None else "",
            value,
        )
        return None
