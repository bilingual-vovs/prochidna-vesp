import time
import uasyncio as asyncio # pyright: ignore[reportMissingImports]
from machine import reset, RTC, freq # type: ignore
from utils import connect, load_credentials, DEFAULT_CONFIG
from buzzer import BuzzerController
import ujson
from led import LedController
from mqtt_manager import MqttManager
from pn532_controller import PN532Controller
from db_conroller import DatabaseController
import ntptime
import json

SOFTWARE = 'v2.15.2-whitelist-operations'

# --- Configuration (Unchanged) ---
CONFIG_FILE = "config.json"

# --- Global State & Hardware Objects ---
data_queue = []; queue_lock = asyncio.Lock()
config = DEFAULT_CONFIG.copy(); whitelist = set(); rtc = RTC()
buzzer = None; led_controller = None; mqtt_manager = None
db_controller = None; pn532_controller = None

# --- Helper Functions ---
def log(message): print(f"[{time.time()}] {message}")

def release():
    """Release all resources"""
    if pn532_controller:
        pn532_controller.stop()
    if mqtt_manager:
        mqtt_manager.disconnect()
    if led_controller:
        led_controller.release()
    log("All resources released.")

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

# --- Hardware Initialization ---
def initialize_hardware():
    global buzzer, led_controller, db_controller, pn532_controller
    log("Initializing hardware...")
    try:
        # Initialize LED controller
        led_controller = LedController(config['LED_GPIO'], config['LED_DIODS_AM'], config)
        asyncio.create_task(led_controller.run())
        
        # Initialize buzzer
        buzzer = BuzzerController(config['BUZZER_GPIO'], 
                                aproval_melody=config['APROVAL_MELODY'], 
                                denial_melody=config['DENIAL_MELODY'])
        
        # Initialize database controller
        db_controller = DatabaseController(log=log)
        
        # Initialize PN532 controller with callbacks
        def nfc_read_callback(data):
            # Add to queue for MQTT publishing
            if mqtt_manager and mqtt_manager.is_connected:
                mqtt_manager.register_read(ujson.dumps(data))
        
        pn532_controller = PN532Controller(config, led_controller, db_controller, nfc_read_callback)
        
        log("Hardware initialized.")
        return True
    except Exception as e:
        log(f"FATAL: Hardware init error: {e}")
        return False

# --- Main ---
async def main():
    global SOFTWARE, mqtt_manager, pn532_controller
    log("Loading software version: " + SOFTWARE)
    load_config(); apply_config()
    
    # Initialize hardware components
    if not initialize_hardware():
        return log("Hardware init failed. Halting.")
        
    # Connect to network
    credits = load_credentials()
    l = connect(config.get("PREFERED_NETWORK", "ethernet"), {}, credits)
    log(f"Network connected. IP info: {l}")
    buzzer.off() # type: ignore

    # Sync time
    try:
        ntptime.settime()
        log("RTC synchronized with NTP. Current time: " + str(rtc.datetime()))
    except Exception as e:
        log(f"Error synchronizing with NTP: {e}") 

    # Initialize and connect the MQTT Manager
    mqtt_manager = MqttManager(
        config=config, 
        led_cb=led_controller.set_annimation,
        whitelist_cb=handle_whitelist_update, 
        config_cb=handle_config_update, 
        reset_cb=release
    )
    if not await mqtt_manager.connect():
        log("Could not connect to MQTT broker. Resetting.")
        reset()
        
    # Start the PN532 controller
    if not await pn532_controller.run():
        log("Could not start PN532 controller. Resetting.")
        reset()
        
    # Start MQTT message loop
    asyncio.create_task(mqtt_manager.message_loop())

    log("All systems running.")
    # The main loop is now only for keeping the script alive
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