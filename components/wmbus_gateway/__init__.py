import esphome.codegen as cg
import esphome.config_validation as cv
from esphome import final_validate
from esphome.components.binary_sensor import BinarySensor
from esphome.components.ssd1306_base import SSD1306
from esphome.components.wmbus_meter.base_sensor import BaseSensor
from esphome.const import CONF_DISPLAY_ID, CONF_ID, CONF_PAGES

gui_ns = cg.esphome_ns.namespace("wmbus_gateway")
DisplayManager = gui_ns.class_("DisplayManager", cg.PollingComponent)

CONF_BUTTON_ID = "button_id"

CODEOWNERS = ["@kubasaw"]
AUTO_LOAD = ["network"]

REGISTERED_SENSORS = []

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_ID): cv.declare_id(DisplayManager),
        cv.GenerateID(CONF_DISPLAY_ID): cv.use_id(SSD1306),
        cv.GenerateID(CONF_BUTTON_ID): cv.use_id(BinarySensor),
        cv.Optional(CONF_PAGES, default=REGISTERED_SENSORS): cv.All(
            lambda x: REGISTERED_SENSORS if x == "all" else x,
            [cv.use_id(BaseSensor)],
        ),
    }
)


def FINAL_VALIDATE_SCHEMA(config):
    if config[CONF_PAGES]:
        return

    try:
        sensors = final_validate.full_config.get().get_config_for_path(["sensor"])
    except KeyError:
        sensors = []

    REGISTERED_SENSORS.extend(
        sensor["id"] for sensor in sensors if sensor.get("platform") == "wmbus_meter"
    )


async def to_code(config):
    manager = cg.new_Pvariable(
        config[CONF_ID],
        await cg.get_variable(config[CONF_DISPLAY_ID]),
        await cg.get_variable(config[CONF_BUTTON_ID]),
    )

    for page in config[CONF_PAGES]:
        cg.add(manager.add_sensor(await cg.get_variable(page)))

    await cg.register_component(manager, config)
