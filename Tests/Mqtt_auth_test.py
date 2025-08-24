from mqtt_manager import MqttManager
import ujson
import time
import uasyncio as asyncio
from utils import connect_wifi, generate_default_reader_id, load_credentials

def log(message):
    print(f"[{time.time()}] MAIN: {message}")

config = {}
CONFIG_FILE = 'config.json'
def load_config():
    global config
    try:
        with open(CONFIG_FILE,'r')as f:config=ujson.load(f);log("Config loaded.")
    except Exception as e:
        log(f"Config load error:{e}")

async def main():
    global config
    credits = load_credentials()
    log(f"Device ID: {credits['CLIENT_ID']}")
    log(f"Reader ID: {credits.get('READER_ID', generate_default_reader_id())}")
    log(credits['WIFI_SSID'] + " : " + credits['WIFI_PASSWORD'])
    connect_wifi(credits['WIFI_SSID'], credits['WIFI_PASSWORD'])

    load_config()

    mqtt_manager = MqttManager(config, led_cb=lambda state, l: log(f"LED state changed to {state}:{l}"),
                            whitelist_cb=lambda action, uid: log(f"Whitelist action: {action} for UID {uid}"),
                            config_cb=lambda var, val: log(f"Config update: {var} = {val}"),
                            reset_cb=lambda: log("Reset triggered"))    

    mqtt_manager.log("Starting MQTT Manager...")

    await mqtt_manager.connect()

    asyncio.create_task(mqtt_manager.message_loop())

asyncio.run(main())
