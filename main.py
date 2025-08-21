import NFC_PN532 as nfc
from machine import Pin, SPI, reset, RTC, freq
import time
import uasyncio as asyncio
from utils import generate_default_reader_id, connect_wifi
from buzzer import BuzzerController
from umqtt.simple import MQTTClient
import ujson
from led import LedController

freq(240000000) # TEMPORARY DECISION, FIX AT FIRST OPPORTUNITY

SOFTWARE = 'v2.10.6-configurable-led'

# --- Configuration ---
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    # --- System Settings ---
    "CONNECTION_CHECK_INTERVAL": 5,
    "CONNECTION_RETRIES": 5,
    "MQTT_RECONNECT_DELAY": 5,
    "NFC_READ_TIMEOUT": 300,
    "MAX_QUEUE_SIZE": 50,
    
    # --- Network Settings (NEW) ---
    "WIFI_SSID": "prohidna",
    "WIFI_PASSWORD": "admin1234",
    
    # --- MQTT Settings ---
    "BROKER_ADDR": '192.168.232.73',
    "READER_ID_AFFIX": generate_default_reader_id(),
    "READ_EVENT_PREFFIX": 'read',
    "WHITELIST_TOPIC_SUFFIX": "whitelist/update",
    "CONFIG_TOPIC_SUFFIX": "configure", 
    "RESET_TOPIC_SUFFIX": "reset",
    
    # --- Hardware Pin Configuration ---
    "BUZZER_GPIO": 4,
    "SPI_SCK_GPIO": 18,
    "SPI_MOSI_GPIO": 23,
    "SPI_MISO_GPIO": 19,
    "NFC_CS_GPIO": 5,
    "LED_GPIO": 32,  
    
    # --- Melodies --- 
    "APROVAL_MELODY": [
        [659, 150], [698, 150], [784, 150], [880, 300]
    ],
    "DENIAL_MELODY":[
        [523, 200], [440, 200], [349, 300]
    ],
    
    # --- Data ---
    "WHITELIST": [],

    # ---LED Settings (NEW)---
    'LED_DIODS_AM': 24,
    'LED_COLOR_SUCCESS': [0, 255, 0],       # Green
    'LED_COLOR_FAILURE': [255, 0, 0],       # Red
    'LED_COLOR_LOADING': [0, 100, 200],     # Light Blue
    'LED_COLOR_WAITING': [0, 50, 100],      # Dimmer Blue
    'LED_COLOR_OFF':     [0, 0, 0],         # Black
    'LED_LOADING_POS': 0,
    'LED_WAITING_PULSE_ANGLE': 0,
    'LED_WAITING_PULSE_SPEED': 0.04
}

# --- Global State ---
pn532 = None
mqttc = None
connected_nfc = False
connected_mqtt = False
last_uid = None
data_queue = []
queue_lock = asyncio.Lock()
config = DEFAULT_CONFIG.copy()
whitelist = set()
rtc = RTC()
led_state = {
    'animation': 'loading', # Initial state
    'duration': 0
}


# --- Global Hardware Objects (to be initialized later) ---
spi_dev = None
cs = None
buzzer = None
led_controller = None


# --- Helper Functions (Unchanged) ---
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

# --- Hardware and NFC Functions (Unchanged) ---
def initialize_hardware():
    """Initializes hardware peripherals based on the loaded configuration."""
    global spi_dev, cs, buzzer, led_controller
    log("Initializing hardware with configured pins...")
    try:
        led_controller = LedController(config['LED_GPIO'], config['LED_DIODS_AM'], led_state,
                                       LIGHT_BLUE=config['LED_COLOR_LOADING'],
                                       PULSE_BLUE=config['LED_COLOR_WAITING'],
                                       GREEN=config['LED_COLOR_SUCCESS'],
                                       RED=config['LED_COLOR_FAILURE'],
                                       BLACK=config['LED_COLOR_OFF'],
                                       
                                       loading_pos=config['LED_LOADING_POS'],
                                       pulse_angle=config['LED_WAITING_PULSE_ANGLE'],
                                       pulse_speed=config['LED_WAITING_PULSE_SPEED'])
        asyncio.create_task(led_controller.run())
        spi_dev = SPI(1, baudrate=1000000,
                      sck=Pin(config['SPI_SCK_GPIO']),
                      mosi=Pin(config['SPI_MOSI_GPIO']),
                      miso=Pin(config['SPI_MISO_GPIO']))
        cs = Pin(config['NFC_CS_GPIO'], Pin.OUT, value=1)
        buzzer = BuzzerController(config['BUZZER_GPIO'])
        log("Hardware initialized successfully.")
        return True
    except Exception as e:
        log(f"FATAL: Error initializing hardware: {e}")
        log("Please check pin configuration in 'config.json'. Device will halt.")
        return False

async def connect_to_pn532():
    global pn532, connected_nfc, led_state
    if pn532 is None:
        pn532 = nfc.PN532(spi_dev, cs)
    retries = 0
    while retries < config["CONNECTION_RETRIES"]:
        led_state['animation'] = 'loading'
        led_state['duration'] = 0  # No duration for loading animation
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
    if mqttc:
        mqttc.publish(f'error/{config["READER_ID_AFFIX"]}', 'Failed to connect to PN532 after multiple retries.')
    log("Failed to connect to PN532 after multiple retries.")
    return False

async def check_pn532_connection():
    global connected_nfc, led_state
    while True:
        await asyncio.sleep(config["CONNECTION_CHECK_INTERVAL"])
        if not connected_nfc:
            log("PN532 connection is down. Attempting to reconnect.")
            await connect_to_pn532()
        else:
            try:
                ic, ver, rev, support = pn532.get_firmware_version()
            except Exception as e:
                led_state['animation'] = 'loading'  # Indicate failure
                led_state['duration'] = 0  # Short duration for failure indication
                log(f"PN532 connection lost: {e}")
                connected_nfc = False

async def indicate(i):
    if i:
        led_state['animation'] = 'success'
        led_state['duration'] = 0.7  
        asyncio.create_task(buzzer.play_melody(config["APROVAL_MELODY"]))
    else:
        led_state['animation'] = 'failure'
        led_state['duration'] = 0.7  
        asyncio.create_task(buzzer.play_melody(config["DENIAL_MELODY"]))

async def read_nfc():
    global last_uid, connected_nfc, data_queue, queue_lock, whitelist,led_state
    while True:
        if connected_nfc:
            led_state['animation'] = 'waiting'  # Pulsing blue
            led_state['duration'] = 0
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
                            asyncio.create_task(indicate(True))
                            async with queue_lock:
                                if len(data_queue) < config["MAX_QUEUE_SIZE"]:
                                    data_queue.append(uid_str_dec)
                                else:
                                    log("Data queue is full. Discarding data.")
                        else:
                            log("Card is NOT whitelisted. Access denied.")
                            asyncio.create_task(indicate(False))
            except Exception as e:
                log(f"Error reading NFC: {e}")
                connected_nfc = False
        await asyncio.sleep(0.1)

# --- MQTT Functions (Unchanged) ---
async def mqtt_connect():
    global mqttc, connected_mqtt, led_state
    mqttc = MQTTClient(config["READER_ID_AFFIX"], config["BROKER_ADDR"], keepalive=120)
    mqttc.set_callback(mqtt_callback)
    retries = 0
    while retries < config["CONNECTION_RETRIES"]:
        led_state['animation'] = 'loading'      
        led_state['duration'] = 0
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
                        log(f"Published data: {data}")
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
        config_var = topic.split('/')[-1]
        try:
            if config_var not in config:
                log(f"Unknown configuration variable: {config_var}")
                return
            
            if isinstance(config[config_var], float):
                value = float(msg)
            elif isinstance(config[config_var], list):
                value = ujson.loads(msg)
            else:
                value = str(msg)

            config[config_var] = value
            log(f"Configuration variable '{config_var}' updated to '{value}'")
            save_config()
            
            vars_that_dont_need_reset = [
                "CONNECTION_CHECK_INTERVAL", "CONNECTION_RETRIES", 
                "MAX_QUEUE_SIZE", "READ_EVENT_PREFFIX"
            ]
            if config_var not in vars_that_dont_need_reset:
                log(f"Resetting device to apply changes for '{config_var}'...")
                reset() 
                
        except Exception as e:
            log(f"Error processing configuration update for '{config_var}': {e}")

# --- Main (Updated) ---
async def main():
    global SOFTWARE, connected_mqtt
    log("Loading software version: " + SOFTWARE)
    load_config()
    apply_config()

    # Initialize hardware AFTER loading config
    if not initialize_hardware():
        log("Hardware initialization failed. The device will not continue.")
        return # Stop execution if hardware fails

    # Use the configured Wi-Fi credentials
    log(f"Connecting to WiFi SSID: {config['WIFI_SSID']}")
    wifi_connected = connect_wifi(config['WIFI_SSID'], config['WIFI_PASSWORD'])
    log("Network connection successful: " + str(wifi_connected))
    
    # This code only runs if hardware was initialized successfully
    buzzer.off()
    
    await connect_to_pn532()
    await mqtt_connect()

    asyncio.create_task(check_pn532_connection())
    asyncio.create_task(read_nfc())
    asyncio.create_task(publish_data())

    led_state['animation'] = 'waiting'  # Start with pulsing blue
    led_state['duration'] = 0  # No duration for pulsing animation

    # Main loop to keep the program running
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
        if pn532:
            log("Releasing NFC resources.")
        if mqttc and connected_mqtt:
            log("Disconnecting from MQTT.")
            mqttc.publish(f'offline/{config["READER_ID_AFFIX"]}', config["READER_ID_AFFIX"])
            mqttc.disconnect()
        led_controller.release()
        log("Done.")