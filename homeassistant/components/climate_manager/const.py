"""Climate manager."""

DOMAIN = "climate_manager"
ENTITY_ID_FORMAT = DOMAIN + ".{}"

CONFIG_MAIN_THERMOSTAT_NAME = "main_thermostat_name"
CONFIG_ZONE_NAME = "zone_name"
CONFIG_REGULATOR_TYPE = "regulator_type"
CONFIG_TEMPERATURE_SENSOR = "temperature_sensor"
CONFIG_WINDOW_SENSORS = "window_sensors"
CONFIG_TRVS = "trvs"
CONFIG_BOILER_STATUS_SENSOR = "boiler_status_sensor"
CONFIG_ZONES = "zones"
CONFIG_SWITCHES = "switches"

REGULATOR_TYPE_PID = "PID"
REGULATOR_TYPE_HYSTERESIS = "Hysteresis"

SUBENTRY_TYPE_ZONE = "zone"
SUBENTRY_TYPE_CIRCUIT = "circuit"

STEP_USER = "user"
STEP_MENU = "menu"
STEP_ENTITIES = "entities"
STEP_BOILER = "boiler"
STEP_ZONES = "heating_zones"
STEP_CIRCUITS = "heating_circuits"
STEP_FINISH = "finish"
