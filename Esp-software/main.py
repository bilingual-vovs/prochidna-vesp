import NFC_PN532 as nfc # type: ignore
from machine import Pin, SPI, reset, RTC, freq # type: ignore
import time
import uasyncio as asyncio # pyright: ignore[reportMissingImports]
from utils import connect, load_credentials, DEFAULT_CONFIG
from buzzer import BuzzerController
import ujson
from led import LedController
from mqtt_manager import MqttManager # <-- NEW IMPORT
import ntptime
import json

SOFTWARE = 'v2.15.2-whitelist-operations'

# --- Configuration (Unchanged) ---
CONFIG_FILE = "config.json"

# --- Global State & Hardware Objects (Simplified) ---
pn532 = None; connected_nfc = False; last_uid = None
data_queue = []; queue_lock = asyncio.Lock()
config = DEFAULT_CONFIG.copy(); whitelist = set(); rtc = RTC()
spi_dev = None; cs = None; buzzer = None; led_controller = None; mqtt_manager = None

# --- Helper Functions ---
def log(message): print(f"[{time.time()}] {message}")

def release():
    if pn532: log("Releasing NFC resources.")
    if mqtt_manager: mqtt_manager.disconnect()
    if led_controller: led_controller.release()
    log("Done.")

def load_config():
    # ... (Unchanged)
    global config;import ujson;from utils import generate_default_reader_id;
    try:
        with open(CONFIG_FILE,'r')as f:config=DEFAULT_CONFIG.copy();config.update(ujson.load(f))
        log("Config loaded.")
        if config["READER_ID_AFFIX"]=="unidentified_reader":config["READER_ID_AFFIX"]=generate_default_reader_id();save_config();log(f"Generated UID:{config['READER_ID_AFFIX']}")
    except Exception as e:log(f"Config load error:{e}.Using defaults.");config=DEFAULT_CONFIG.copy();save_config()

def save_config():
    try:
        with open(CONFIG_FILE,'w')as f:ujson.dump(config,f);log("Config saved.")
    except Exception as e:log(f"Config save error:{e}")

def apply_config():
  global whitelist; whitelist = set(config.get("WHITELIST", []))

# --- NEW: MQTT Callback Handlers ---
def handle_whitelist_update(action, data):
    """Callback function for the MqttManager to handle whitelist messages."""
    if action == "add":
        for entry in data:
            if entry not in whitelist:
                whitelist.add(entry)
                log(f"Whitelist entry added: {entry}")
            else:
                log(f"Whitelist entry already exists: {entry}")
    elif action == "remove":
        for entry in data:  
            if entry in whitelist:
                whitelist.remove(entry)
                log(f"Whitelist entry removed: {entry}")
            else:
                log(f"Whitelist entry not found: {entry}")  
    elif action == "update":                            
        if isinstance(data, list):
            whitelist.clear()
            whitelist.update(data)
            log("Whitelist updated.")
        else:
            log("Invalid data for whitelist update. Expected a list.")
    global config; config["WHITELIST"] = whitelist
    apply_config(); save_config()
    log("Whitelist update applied.")

def handle_config_update(config_var, msg):
    """Callback function for the MqttManager to handle config messages."""
    global config, mqtt_manager
    try:
        if config_var not in config: return log(f"Unknown config var: {config_var}")
        # Your type conversion logic
        if isinstance(config[config_var], float): value = float(msg)
        elif isinstance(config[config_var], int): value = int(msg)
        elif isinstance(config[config_var], list): value = ujson.loads(msg)
        else: value = str(msg)
        config[config_var] = value
        log(f"Config '{config_var}' updated to '{value}'")
        save_config()
        # Reset if the changed variable requires it
        if config_var not in ["CONNECTION_CHECK_INTERVAL", "CONNECTION_RETRIES", "MAX_QUEUE_SIZE", "READ_EVENT_PREFFIX"]:
            log(f"Resetting to apply changes for '{config_var}'..."); reset()
    except Exception as e:
        log(f"Error processing config update for '{config_var}': {e}")
        mqtt_manager.register_error(f"Error processing config update for '{config_var}': {e}") # type: ignore

# --- Hardware and NFC (Slightly simplified) ---
def initialize_hardware():
    global spi_dev, cs, buzzer, led_controller
    log("Initializing hardware...")
    try:
        led_controller = LedController(config['LED_GPIO'], config['LED_DIODS_AM'], config)
        asyncio.create_task(led_controller.run())
        spi_dev = SPI(1, baudrate=1000000, sck=Pin(config['SPI_SCK_GPIO']), mosi=Pin(config['SPI_MOSI_GPIO']), miso=Pin(config['SPI_MISO_GPIO']))
        cs = Pin(config['NFC_CS_GPIO'], Pin.OUT, value=1)
        buzzer = BuzzerController(config['BUZZER_GPIO'], aproval_melody=config['APROVAL_MELODY'], denial_melody=config['DENIAL_MELODY'])
        log("Hardware initialized."); return True
    except Exception as e:
        log(f"FATAL: Hardware init error: {e}"); return False

# ... (connect_to_pn532, check_pn532_connection, indicate, read_nfc are unchanged) ...
async def connect_to_pn532():
    global pn532, connected_nfc, led_controller
    if pn532 is None:
        pn532 = nfc.PN532(spi_dev, cs)
    retries = 0
    while retries < config["CONNECTION_RETRIES"]:
        led_controller.set_annimation('loading')  # type: ignore # Set loading animation
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
    global connected_nfc, led_controller
    while True:
        await asyncio.sleep(config["CONNECTION_CHECK_INTERVAL"])
        if not connected_nfc:
            log("PN532 connection is down. Attempting to reconnect.")
            await connect_to_pn532()
        else:
            try:
                ic, ver, rev, support = pn532.get_firmware_version() # type: ignore
            except Exception as e:
                led_controller.set_annimation("loading") # type: ignore # Short duration for failure indication
                log(f"PN532 connection lost: {e}")
                mqtt_manager.register_error(f"PN532 connection lost: {e}") # type: ignore
                connected_nfc = False

                

async def read_nfc():
    global last_uid, connected_nfc, data_queue, queue_lock, whitelist
    while True:
        if connected_nfc:
            led_controller.set_annimation('waiting')  # type: ignore # Set loading animation
            try:
                uid = pn532.read_passive_target(timeout=config["NFC_READ_TIMEOUT"]) # type: ignore
                if uid is not None:
                    code = nfc.read_card_code_from_block4(pn532, uid)
                    uid_str_hex = '-'.join(['{:02X}'.format(i) for i in uid])
                    uid_str_dec = '-'.join([str(i) for i in uid])
                    if uid != last_uid:
                        last_uid = uid
                        log(f"Card Found! UID (hexadecimal): {uid_str_hex}, UID (decimal): {uid_str_dec}")
                        if uid_str_dec or code:
                            log("Card is whitelisted. Access granted.")
                            led_controller.set_annimation('success', 0.7) # type: ignore
                            asyncio.create_task(buzzer.play_approval())  # type: ignore # Play approval melody
                            async with queue_lock:
                                if len(data_queue) < config["MAX_QUEUE_SIZE"]:
                                    data = {
                                        "uid_dec": uid_str_dec,
                                        "code": code,
                                        "timestamp": time.time()
                                    }
                                    data_queue.append(json.dumps(data))
                                else:
                                    log("Data queue is full. Discarding data.")
                        else:
                            log("Card is NOT whitelisted. Access denied.")
                            led_controller.set_annimation('failure', 0.7) # type: ignore
                            asyncio.create_task(buzzer.play_denial())  # type: ignore # Play denial melody
            except Exception as e:
                log(f"Error reading NFC: {e}")
                mqtt_manager.register_error(f"Error reading NFC: {e}") # type: ignore
                connected_nfc = False
        await asyncio.sleep(0.01)

# --- NEW: Task to publish queued data ---
async def publish_queued_data():
    global data_queue, queue_lock, mqtt_manager
    while True:
        async with queue_lock:
            if data_queue:
                data = data_queue.pop(0)
                # Use the MqttManager to publish
                mqtt_manager.register_read(data) # type: ignore
        await asyncio.sleep(0.1)

# --- Main (Heavily updated) ---
async def main():
    global SOFTWARE, mqtt_manager
    log("Loading software version: " + SOFTWARE)
    load_config(); apply_config()
    if not initialize_hardware(): return log("Hardware init failed. Halting.")
    credits = load_credentials()
    
    l = connect(config.get("PREFERED_NETWORK", "ethernet"), {}, credits)
    log(f"Network connected. IP info: {l}")
    buzzer.off() # type: ignore

    try:
        ntptime.settime()
        log("RTC synchronized with NTP. Current time: " + str(rtc.datetime()))
    except Exception as e:
        log(f"Error synchronizing with NTP: {e}") 

    # Initialize and connect the MQTT Manager
    mqtt_manager = MqttManager(
        config=config, led_cb=led_controller.set_annimation, # Assumes LedController has such a method # type: ignore
        whitelist_cb=handle_whitelist_update, config_cb=handle_config_update, reset_cb=release
    )
    if not await mqtt_manager.connect():
        log("Could not connect to MQTT broker. Resetting."); reset()
        
    # Start all background tasks
    await connect_to_pn532()
    asyncio.create_task(check_pn532_connection())
    asyncio.create_task(read_nfc())
    asyncio.create_task(publish_queued_data())
    asyncio.create_task(mqtt_manager.message_loop()) # This replaces the old check_msg in the main loop

    log("All systems running.")
    # The main loop is now only for keeping the script alive.
    while True:
        await asyncio.sleep(60)

# --- Entry Point ---
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("Exiting...")
    finally:
        release()