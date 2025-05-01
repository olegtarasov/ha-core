"""Climate manager."""

DOMAIN = "climate_manager"
ENTITY_ID_FORMAT = DOMAIN + ".{}"

CONFIG_MAIN_THERMOSTAT_NAME = "main_thermostat_name"
CONFIG_ZONE_NAME = "zone_name"
CONFIG_TEMPERATURE_SENSOR = "temperature_sensor"
CONFIG_WINDOW_SENSORS = "window_sensors"
CONFIG_TRVS = "trvs"

SUBENTRY_TYPE_ZONE = "zone"
SUBENTRY_TYPE_CIRCUIT = "circuit"

STEP_USER = "user"
STEP_MENU = "menu"
STEP_ENTITIES = "entities"
STEP_ZONES = "heating_zones"
STEP_CIRCUITS = "heating_circuits"
STEP_FINISH = "finish"
