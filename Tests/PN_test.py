from pn532_controller import PN532Controller
from led import LedController
from db_conroller import DatabaseController
from mqtt_manager import MqttManager
from utils import DEFAULT_CONFIG as conf
import uasyncio as asyncio

led = LedController(2, 24, conf)
db = DatabaseController()
mqtt = MqttManager(conf, print, print, db)

pn = PN532Controller(conf, led, db, mqtt)

print(conf["SPI_MISO_GPIO"])

asyncio.run(pn.run())