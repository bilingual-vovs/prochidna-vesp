# --- MODIFIED FOR EMULATION ---
# No longer imports NFC_PN532
from machine import Pin, reset, RTC, SPI
import time
import uasyncio as asyncio
from utils import blink, generate_default_reader_id
from buzzer import BuzzerController
from umqtt.simple import MQTTClient
import ujson
from light import Light_controller
import urandom # Import for random intervals and card selection

SOFTWARE = 'v2.7.3-EMULATED'

# --- Configuration ---
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "CONNECTION_CHECK_INTERVAL": 5,
    "CONNECTION_RETRIES": 5,
    "BROKER_ADDR": '192.168.232.73',
    "MQTT_RECONNECT_DELAY": 5,
    "MAX_QUEUE_SIZE": 50,
    "WHITELIST": [], 
    "READER_ID_AFFIX": generate_default_reader_id(),
    "READ_EVENT_PREFFIX": 'read',
    "WHITELIST_TOPIC_SUFFIX": "whitelist/update",
    "CONFIG_TOPIC_SUFFIX": "configure", 
    "RESET_TOPIC_SUFFIX": "reset",
    "BUZZER_GPIO": 4,
    "APROVAL_MELODY": [
        [659, 150], [698, 150], [784, 150], [880, 300]
    ],
    "DENIAL_MELODY":[
        [523, 200], [440, 200], [349, 300]
    ]
}

# --- Global State ---
mqttc = None
connected_mqtt = False
data_queue = []
queue_lock = asyncio.Lock()
config = DEFAULT_CONFIG.copy()
whitelist = set()
rtc = RTC()

# --- Hardware Setup ---
# --- PN532 hardware setup removed for emulation ---
# spi_dev = SPI(1, baudrate=1000000, sck=Pin(18), mosi=Pin(23), miso=Pin(19))
# cs = Pin(5, Pin.OUT, value=1)
buzzer = BuzzerController(config['BUZZER_GPIO'])
buzzer.off()
light = Light_controller(15, 16)

# --- Helper Functions ---
def log(message):
    print(f"[{time.time()}] {message}")

def load_config():
    global config
    try:
        with open(CONFIG_FILE, 'r') as f:
            config = ujson.load(f)
        log("Configuration loaded from file.")
        if config["READER_ID_AFFIX"] == "unidentified_reader": 
            config["READER_ID_AFFIX"] = generate_default_reader_id()
            save_config()
            log("Generated UID for reader: " + config['READER_ID_AFFIX'])
    except Exception as e:
        log(f"Error loading configuration: {e}. Using defaults.")
        config = DEFAULT_CONFIG.copy()
        save_config()

def save_config():
    try:
        with open(CONFIG_FILE, 'w') as f:
            ujson.dump(config, f)
        log("Configuration saved to file.")
    except Exception as e:
        log(f"Error saving configuration: {e}")

def apply_config():
  global whitelist
  whitelist = set(config.get("WHITELIST", []))

# --- NFC Functions (Now Emulation) ---
async def indicate(i):
    if i:
        asyncio.create_task(light.light_green(1))
        asyncio.create_task(buzzer.play_melody(config["APROVAL_MELODY"]))
    else:
        asyncio.create_task(light.light_red(1))
        asyncio.create_task(buzzer.play_melody(config["DENIAL_MELODY"]))

async def emulate_card_read():
    """
    This function replaces the real NFC reading logic.
    It waits for a random interval, then picks a card from the
    whitelist and adds it to the queue to be published.
    """
    global data_queue, queue_lock, whitelist
    log("Starting card emulation mode.")

    while True:
        # Wait for a random interval between 10 and 15 seconds
        delay = urandom.uniform(45, 120)
        await asyncio.sleep(delay)

        if not whitelist:
            log("Whitelist is empty. Cannot emulate a card read. Please update config.")
            continue # Skip this iteration and wait again

        try:
            # Randomly pick a card UID from the whitelist
            # Convert set to list to allow random.choice
            uid_to_emulate = urandom.choice(list(whitelist))
            
            log(f"EMULATED Card Read! UID: {uid_to_emulate}")
            
            # Since the card is from the whitelist, we always indicate success
            asyncio.create_task(indicate(True))
            
            async with queue_lock:
                if len(data_queue) < config["MAX_QUEUE_SIZE"]:
                    data_queue.append(uid_to_emulate)
                    blink(3, delay_ms=30)
                else:
                    log("Data queue is full. Discarding emulated data.")

        except Exception as e:
            log(f"Error during card emulation: {e}")

# --- MQTT Functions (Largely Unchanged) ---
async def mqtt_connect():
    global mqttc, connected_mqtt
    mqttc = MQTTClient(config["READER_ID_AFFIX"], config["BROKER_ADDR"], keepalive=60)
    mqttc.set_callback(mqtt_callback)
    retries = 0
    while retries < config["CONNECTION_RETRIES"]:
        try:
            mqttc.connect()
            mqttc.subscribe(f'{config["READER_ID_AFFIX"]}/{config["WHITELIST_TOPIC_SUFFIX"]}')
            mqttc.subscribe(f"{config["READER_ID_AFFIX"]}/{config['CONFIG_TOPIC_SUFFIX']}/#")
            mqttc.subscribe(f'{config["READER_ID_AFFIX"]}/{config["RESET_TOPIC_SUFFIX"]}')
            mqttc.set_last_will(topic=f'offline/{config["READER_ID_AFFIX"]}', msg=config["READER_ID_AFFIX"], retain=True, qos=2)
            mqttc.publish(f'online/{config["READER_ID_AFFIX"]}', config["READER_ID_AFFIX"])
            log("Connected to MQTT Broker")
            connected_mqtt = True
            return True
        except Exception as e:
            log(f"MQTT Connection failed: {e}, retrying in {config['MQTT_RECONNECT_DELAY']} seconds...")
            retries += 1
            await asyncio.sleep(config["MQTT_RECONNECT_DELAY"])
    log("Failed to connect to MQTT after multiple retries.")
    reset()
    return False

async def publish_data():
    global connected_mqtt, data_queue, queue_lock
    while True:
        if connected_mqtt:
            async with queue_lock:
                if data_queue:
                    data = data_queue.pop(0)
                    try:
                        mqttc.publish(f'{config["READ_EVENT_PREFFIX"]}/{config["READER_ID_AFFIX"]}', "+Fake data: " + str(data))
                        log(f"Published emulated data: {data}")
                    except Exception as e:
                        log(f"Error publishing data: {e}")
                        data_queue.insert(0, data)
        await asyncio.sleep(0.1)

def mqtt_callback(topic, msg):
    global config, whitelist
    topic = topic.decode('utf-8')
    msg = msg.decode('utf-8')
    log(f"Received MQTT message on topic: {topic}, message: {msg}")

    if topic == f'{config["READER_ID_AFFIX"]}/{config["WHITELIST_TOPIC_SUFFIX"]}':
        try:
            new_whitelist = ujson.loads(msg)
            if isinstance(new_whitelist, list):
                config["WHITELIST"] = new_whitelist
                apply_config()
                save_config()
                log("Whitelist updated successfully.")
            else:
                log("Invalid whitelist format. Expected a list.")
        except Exception as e:
            log(f"Error processing whitelist update: {e}")
    elif topic.startswith(f'{config["READER_ID_AFFIX"]}/{config["CONFIG_TOPIC_SUFFIX"]}/'):
        config_var = topic[len(f'{config["READER_ID_AFFIX"]}/{config["CONFIG_TOPIC_SUFFIX"]}') + 1:]
        try:
            if config_var in ("CONNECTION_CHECK_INTERVAL", "CONNECTION_RETRIES", "MQTT_RECONNECT_DELAY", "NFC_READ_TIMEOUT", "MAX_QUEUE_SIZE"):
                value = int(msg)
            else:
                value = str(msg)

            config[config_var] = value
            log(f"Configuration variable '{config_var}' updated to '{value}'")
            save_config()
            if not config_var in ["CONNECTION_CHECK_INTERVAL", "CONNECTION_RETRIES", "MAX_QUEUE_SIZE", "READ_EVENT_PREFFIX"]:
                reset() 
        except Exception as e:
            log(f"Error processing configuration update for '{config_var}': {e}")


# --- Main ---
async def main():
    global SOFTWARE, connected_mqtt
    log("Loading software version: " + SOFTWARE)
    load_config()
    apply_config()

    light.off()
    await mqtt_connect()
    buzzer.off()

    # Start the emulation task instead of the real NFC tasks
    asyncio.create_task(emulate_card_read())
    asyncio.create_task(publish_data())

    while True:
        try:
            mqttc.check_msg()
            await asyncio.sleep(0.1)
        except Exception as e:
            connected_mqtt = False
            await mqtt_connect()
            if connected_mqtt: pass
            
            log(f"Unrecoverable error in main loop: {e}")
            mqttc.publish(f'error/{config["READER_ID_AFFIX"]}', f'Unrecoverable error in main loop. {e}. Resetting device.')
            log("Resetting due to unrecoverable error.")
            reset()

# --- Entry Point ---
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("Exiting...")
    finally:
        if mqttc:
            log("Disconnecting from MQTT.")
            mqttc.publish(f'offline/{config["READER_ID_AFFIX"]}', config["READER_ID_AFFIX"])
            mqttc.disconnect()
        log("Done.")