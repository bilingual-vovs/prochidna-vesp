# Imports for emulation, networking, and RGB LED
from machine import Pin, reset, RTC
import time
import uasyncio as asyncio
import urandom
import neopixel
from utils import generate_default_reader_id, connect_wifi
from umqtt.simple import MQTTClient
import ujson

SOFTWARE = 'v3.0.0-EMULATOR'

# --- Configuration ---
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    # --- System Settings ---
    "CONNECTION_CHECK_INTERVAL": 5,
    "CONNECTION_RETRIES": 5,
    "MQTT_RECONNECT_DELAY": 5,
    "MAX_QUEUE_SIZE": 50,
    
    # --- MQTT Settings ---
    "BROKER_ADDR": '192.168.232.73',
    "READER_ID_AFFIX": generate_default_reader_id(),
    "READ_EVENT_PREFFIX": 'read',
    "WHITELIST_TOPIC_SUFFIX": "whitelist/update",
    "CONFIG_TOPIC_SUFFIX": "configure", 
    "RESET_TOPIC_SUFFIX": "reset",
    
    # --- Hardware Pin Configuration ---
    "RGB_LED_GPIO": 21, # Pin for the onboard WS2812 LED
    "RGB_CYCLE_SPEED_MS": 15, # Speed of the rainbow effect
    
    # --- Data ---
    "WHITELIST": []
}

# --- Global State ---
mqttc = None
connected_mqtt = False
data_queue = []
queue_lock = asyncio.Lock()
config = DEFAULT_CONFIG.copy()
whitelist = set()
rtc = RTC()

# --- Global Hardware Objects ---
neopixel_obj = None

# --- Helper Functions ---
def log(message):
    print(f"[{time.time()}] {message}")

def load_config():
    global config
    try:
        with open(CONFIG_FILE, 'r') as f:
            loaded_c = ujson.load(f)
            config = DEFAULT_CONFIG.copy()
            config.update(loaded_c)
        log("Configuration loaded and merged with defaults.")
        if config["READER_ID_AFFIX"] == "unidentified_reader": 
            config["READER_ID_AFFIX"] = generate_default_reader_id()
            save_config()
            log("Generated UID for reader: " + config['READER_ID_AFFIX'])
    except Exception as e:
        log(f"Error loading configuration: {e}. Using and saving defaults.")
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

def initialize_hardware():
    """Initializes hardware peripherals based on the loaded configuration."""
    global neopixel_obj
    log("Initializing hardware with configured pins...")
    try:
        pin = Pin(config['RGB_LED_GPIO'], Pin.OUT)
        neopixel_obj = neopixel.NeoPixel(pin, 1) # One LED
        log("Hardware (RGB LED) initialized successfully.")
        return True
    except Exception as e:
        log(f"FATAL: Error initializing hardware: {e}")
        return False

# --- RGB LED and Emulation Functions ---
def color_wheel(pos):
    """Generates a color from the rainbow. Input 'pos' is 0-255."""
    if pos < 85:
        return (int(pos * 3), int(255 - pos * 3), 0)
    elif pos < 170:
        pos -= 85
        return (int(255 - pos * 3), 0, int(pos * 3))
    else:
        pos -= 170
        return (0, int(pos * 3), int(255 - pos * 3))

async def rgb_led_cycle():
    """Continuously cycles the onboard RGB LED through the rainbow."""
    log("Starting RGB LED rainbow cycle.")
    position = 0
    while True:
        if neopixel_obj:
            neopixel_obj[0] = color_wheel(position)
            neopixel_obj.write()
            position = (position + 1) % 256
        await asyncio.sleep_ms(config['RGB_CYCLE_SPEED_MS'])

async def emulate_reader_activity():
    """Emulates a real reader by posting card reads and occasional errors."""
    log("Starting reader emulation mode.")
    while True:
        delay = urandom.uniform(45, 120)
        log(f"Next emulated event in {delay:.1f} seconds...")
        await asyncio.sleep(delay)

        # Decide whether to send a read or a fake error (e.g., 10% chance of error)
        if urandom.randint(1, 10) == 1:
            log("EMULATING a fake error.")
            if connected_mqtt:
                try:
                    mqttc.publish(f'error/{config["READER_ID_AFFIX"]}', 'fake error')
                except Exception as e:
                    log(f"Failed to publish fake error: {e}")
        else:
            if not whitelist:
                log("Whitelist is empty. Cannot emulate a card read.")
                continue
            
            uid_to_emulate = urandom.choice(list(whitelist))
            log(f"EMULATING Card Read! UID: {uid_to_emulate}")
            async with queue_lock:
                if len(data_queue) < config["MAX_QUEUE_SIZE"]:
                    data_queue.append(uid_to_emulate)
                else:
                    log("Data queue is full. Discarding emulated data.")

# --- MQTT Functions ---
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
                        mqttc.publish(f'{config["READ_EVENT_PREFFIX"]}/{config["READER_ID_AFFIX"]}', str(data))
                        log(f"Published emulated data: {data}")
                    except Exception as e:
                        log(f"Error publishing data: {e}")
                        data_queue.insert(0, data)
        await asyncio.sleep(0.1)

def mqtt_callback(topic, msg):
    """Handles incoming MQTT messages."""
    global config, whitelist
    topic = topic.decode('utf-8')
    msg = msg.decode('utf-8')
    log(f"Received MQTT message on topic: {topic}, message: {msg}")
    
    if topic == f'{config["READER_ID_AFFIX"]}/{config["WHITELIST_TOPIC_SUFFIX"]}':
        # ... Whitelist update logic ...
        pass # Unchanged from your code
    elif topic.startswith(f'{config["READER_ID_AFFIX"]}/{config["CONFIG_TOPIC_SUFFIX"]}/'):
        # ... Config update logic ...
        pass # Unchanged from your code

# --- Main ---
async def main():
    global SOFTWARE, connected_mqtt
    log("Loading software version: " + SOFTWARE)
    load_config()
    apply_config()

    if not initialize_hardware():
        return

    log("Network config: " + str(connect_wifi('s5', 'opelvectra')))
    
    await mqtt_connect()

    # Create asynchronous tasks for the emulator
    asyncio.create_task(rgb_led_cycle())
    asyncio.create_task(emulate_reader_activity())
    asyncio.create_task(publish_data())

    # Main loop to keep MQTT connection alive
    while True:
        try:
            mqttc.check_msg()
            await asyncio.sleep(0.1)
        except Exception as e:
            log(f"Error in main loop, attempting MQTT reconnect: {e}")
            connected_mqtt = False
            await mqtt_connect()
            if not connected_mqtt:
                log("MQTT reconnect failed. Resetting device.")
                reset()

# --- Entry Point ---
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("Exiting...")
    finally:
        if neopixel_obj:
            neopixel_obj[0] = (0, 0, 0) # Turn off LED on exit
            neopixel_obj.write()
        if mqttc and connected_mqtt:
            log("Disconnecting from MQTT.")
            mqttc.publish(f'offline/{config["READER_ID_AFFIX"]}', config["READER_ID_AFFIX"])
            mqttc.disconnect()
        log("Done.")