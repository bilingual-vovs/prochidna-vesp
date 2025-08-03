import NFC_PN532 as nfc
from machine import Pin, SPI, reset, RTC
import time
import uasyncio as asyncio
from utils import blink, indicate  # Import indicate
from umqtt.simple import MQTTClient
import ujson
import os

# --- Configuration ---
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "CONNECTION_CHECK_INTERVAL": 5,
    "CONNECTION_RETRIES": 5,
    "CLIENT_NAME": 'blue',
    "BROKER_ADDR": '192.168.232.73',
    "MQTT_RECONNECT_DELAY": 5,
    "NFC_READ_TIMEOUT": 300,
    "DATA_PUBLISH_TOPIC": 'read',
    "WHITELIST_TOPIC": "whitelist/update",
    "CONFIG_TOPIC_PREFIX": "configure", # New: Configuration topic prefix
    "MAX_QUEUE_SIZE": 50,
    "WHITELIST": [] # Initial empty whitelist
}

# --- Hardware Setup ---
spi_dev = SPI(1, baudrate=1000000, sck=Pin(18), mosi=Pin(23), miso=Pin(19))
cs = Pin(5, Pin.OUT, value=1)

# --- Global State ---
pn532 = None
mqttc = None
connected_nfc = False
connected_mqtt = False
last_uid = None
data_queue = []  # Use a list as a queue
queue_lock = asyncio.Lock()  # Use a lock to protect the queue
config = DEFAULT_CONFIG.copy()  # Make a copy to work with
whitelist = set()  # Store whitelist as a set for fast lookups
rtc = RTC() # Real time clock for synchronize time

# --- Helper Functions ---
def log(message):
    print(f"[{time.time()}] {message}")

def load_config():
    global config
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = ujson.load(f)
        log("Configuration loaded from file.")
    except Exception as e:
        log(f"Error loading configuration: {e}. Using defaults.")
        config = DEFAULT_CONFIG.copy()
        save_config()  # Save defaults

def save_config():
    try:
        with open(CONFIG_FILE, 'w') as f:
            ujson.dump(config, f)
        log("Configuration saved to file.")
    except Exception as e:
        log(f"Error saving configuration: {e}")

def apply_config():
  """Applies loaded configuration.  Used when config is loaded/reloaded."""
  global whitelist
  whitelist = set(config.get("WHITELIST", [])) # Load whitelist into set

# --- NFC Functions ---
async def connect_to_pn532():
    global pn532, connected_nfc
    if pn532 is None:
        pn532 = nfc.PN532(spi_dev, cs)
    retries = 0
    while retries < config["CONNECTION_RETRIES"]:
        try:
            ic, ver, rev, support = pn532.get_firmware_version()
            log('PN532 found, firmware version: {0}.{1}'.format(ver, rev))
            pn532.SAM_configuration()
            connected_nfc = True
            return True
        except RuntimeError as e:
            log(f"Error connecting to PN532: {e}. Retrying...")
            retries += 1
            await asyncio.sleep(1)
    log("Failed to connect to PN532 after multiple retries.")
    return False

async def check_pn532_connection():
    global connected_nfc
    while True:
        await asyncio.sleep(config["CONNECTION_CHECK_INTERVAL"])
        if not connected_nfc:
            log("PN532 connection is down. Attempting to reconnect.")
            await connect_to_pn532()
        else:
            try:
                ic, ver, rev, support = pn532.get_firmware_version()
            except Exception as e:
                log(f"PN532 connection lost: {e}")
                connected_nfc = False

async def read_nfc():
    global last_uid, connected_nfc, data_queue, queue_lock, whitelist

    while True:
        if connected_nfc:
            try:
                uid = pn532.read_passive_target(timeout=config["NFC_READ_TIMEOUT"])
                if uid is not None:
                    uid_str_hex = '-'.join(['{:02X}'.format(i) for i in uid])
                    uid_str_dec = '-'.join([str(i) for i in uid])

                    if uid != last_uid:
                        last_uid = uid
                        log(f"Card Found! UID (hexadecimal): {uid_str_hex}, UID (decimal): {uid_str_dec}")

                        if uid_str_dec in whitelist:
                            log("Card is whitelisted. Access granted.")
                            indicate(True) # Indicate whitelisted card
                            async with queue_lock:  # Acquire the lock before modifying the queue
                                if len(data_queue) < config["MAX_QUEUE_SIZE"]:
                                    data_queue.append(uid_str_dec)
                                    blink(3, delay_ms=30)
                                else:
                                    log("Data queue is full. Discarding data.")  # Handle overflow
                        else:
                            log("Card is NOT whitelisted. Access denied.")
                            indicate(False) # Indicate not whitelisted card

            except Exception as e:
                log(f"Error reading NFC: {e}")
                connected_nfc = False
        await asyncio.sleep(0.1)

# --- MQTT Functions ---
async def mqtt_connect():
    global mqttc, connected_mqtt
    mqttc = MQTTClient(config["CLIENT_NAME"], config["BROKER_ADDR"], keepalive=60)
    mqttc.set_callback(mqtt_callback) # Set the callback
    retries = 0
    while retries < config["CONNECTION_RETRIES"]:
        try:
            mqttc.connect()
            mqttc.subscribe(config["WHITELIST_TOPIC"])  # Subscribe to whitelist topic
            mqttc.subscribe(f"{config['CONFIG_TOPIC_PREFIX']}/#") # New: Subscribe to config topics
            log("Connected to MQTT Broker")
            connected_mqtt = True
            return True
        except Exception as e:
            log(f"MQTT Connection failed: {e}, retrying in {config['MQTT_RECONNECT_DELAY']} seconds...")
            retries += 1
            await asyncio.sleep(config["MQTT_RECONNECT_DELAY"])
    log("Failed to connect to MQTT after multiple retries.")
    return False

async def check_mqtt_connection():
    global connected_mqtt
    while True:
        await asyncio.sleep(config["CONNECTION_CHECK_INTERVAL"])
        if not connected_mqtt:
            log("MQTT connection is down. Attempting to reconnect.")
            await mqtt_connect()
        else:
            try:
                mqttc.ping()
            except Exception as e:
                log(f"MQTT connection lost: {e}")
                connected_mqtt = False

async def publish_data():
    global connected_mqtt, data_queue, queue_lock
    while True:
        if connected_mqtt:
            async with queue_lock:  # Acquire the lock before modifying the queue
                if data_queue:
                    data = data_queue.pop(0)  # Pop from the beginning of the list (FIFO)
                    try:
                        mqttc.publish(config["DATA_PUBLISH_TOPIC"], str(data))
                        log(f"Published data: {data}")
                    except Exception as e:
                        log(f"Error publishing data: {e}")
                        # Consider re-adding the data to the queue if the publish fails
                        data_queue.insert(0, data)  # Add back to the beginning
        await asyncio.sleep(0.1)

def mqtt_callback(topic, msg):
    """Handles incoming MQTT messages."""
    global config, whitelist

    topic = topic.decode('utf-8')
    msg = msg.decode('utf-8')
    log(f"Received MQTT message on topic: {topic}, message: {msg}")

    if topic == config["WHITELIST_TOPIC"]:
        try:
            new_whitelist = ujson.loads(msg)
            if isinstance(new_whitelist, list):
                config["WHITELIST"] = new_whitelist  # Update config
                apply_config() # Apply it
                save_config()  # Save the updated config
                log("Whitelist updated successfully.")
            else:
                log("Invalid whitelist format. Expected a list.")
        except Exception as e:
            log(f"Error processing whitelist update: {e}")
    elif topic.startswith(config["CONFIG_TOPIC_PREFIX"] + "/"):
        config_var = topic[len(config["CONFIG_TOPIC_PREFIX"]) + 1:] # Extract variable name
        try:
            # Attempt to convert the message to the correct type
            if config_var in ("CONNECTION_CHECK_INTERVAL", "CONNECTION_RETRIES", "MQTT_RECONNECT_DELAY", "NFC_READ_TIMEOUT", "MAX_QUEUE_SIZE"):
                value = int(msg)
            elif config_var in ("CLIENT_NAME", "BROKER_ADDR", "DATA_PUBLISH_TOPIC", "WHITELIST_TOPIC", "CONFIG_TOPIC_PREFIX"):
                value = str(msg)
            else:
                log(f"Unknown configuration variable: {config_var}")
                return

            config[config_var] = value
            log(f"Configuration variable '{config_var}' updated to '{value}'")
            save_config() # Save it
        except ValueError:
            log(f"Invalid value for configuration variable '{config_var}': {msg}")
        except Exception as e:
            log(f"Error processing configuration update for '{config_var}': {e}")

# --- Main ---
async def main():
    load_config() # Load configuration from file
    apply_config() # Apply configuration

    await connect_to_pn532()
    await mqtt_connect()

    asyncio.create_task(check_pn532_connection())
    asyncio.create_task(check_mqtt_connection())
    asyncio.create_task(read_nfc())
    asyncio.create_task(publish_data())

    # Main loop to keep the program running
    while True:
        try:
            mqttc.check_msg() # Check for incoming MQTT messages
            await asyncio.sleep(0.1)
        except Exception as e:
            log(f"Error in main loop: {e}")

# --- Entry Point ---
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("Exiting...")
    finally:
        if pn532:
            log("Releasing NFC resources.")
        if mqttc:
            log("Disconnecting from MQTT.")
            mqttc.disconnect()
        log("Done.")