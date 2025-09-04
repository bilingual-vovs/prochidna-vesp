def generate_default_reader_id():
    """Generates a default reader ID based on the MAC address."""
    import network, binascii # type: ignore
    wlan = network.WLAN(network.STA_IF)
    mac = wlan.config('mac')
    mac_str = binascii.hexlify(mac).decode('utf-8')
    return 'unidentified_reader/' + mac_str

DEFAULT_CONFIG = {
  "LED_LOADING_POS": 0,
  "WIFI_SSID": "s5",
  "MQTT_NAMING_TEMPLATE_SUBSCRIBE": "device/$READER_ID_AFFIX/manage/#",
  "MQTT_NAMING_TEMPLATE_PUBLISH": "device/$READER_ID_AFFIX/events/#",
  "LED_COLOR_OFF": [0, 0, 0],
  "MANAGE_WHITELIST": "whitelist/",
  "MANAGE_WHITELIST_ADD": "add",
  "MANAGE_WHITELIST_REMOVE": "remove",
  "MANAGE_RESET": "reset",
  "MAX_QUEUE_SIZE": 50,
  "ERROR_EVENT": "error",
  "LED_COLOR_SUCCESS": [0, 255, 0],
  "MQTT_DELAY": 50,
  "READ_EVENT": "read",
  "ONLINE_EVENT": "online",
  "LED_COLOR_LOADING": [255, 156, 256],
  "DENIAL_MELODY": [
    [430, 100],
    [320, 100]
  ],
  "MANAGE_CONFIG": "configure",
  "LED_WAITING_PULSE_SPEED": 0.1,
  "CLIENT_NAME": "blue",
  "BROKER_ADDR": "192.168.31.70",
  "LED_WAITING_PULSE_ANGLE": 0,
  "CONNECTION_CHECK_INTERVAL": 5,
  "WIFI_PASSWORD": "opelvectra",
  "CONNECTION_RETRIES": 15,
  "OFFLINE_EVENT": "offline",
  "MQTT_RECONNECT_DELAY": 10,
  "NFC_READ_TIMEOUT": 9,
  "LED_DIODS_AM": 24,
  "APROVAL_MELODY": [
    [700, 100],
    [880, 100]
  ],
  "READER_ID_AFFIX": "reader_real",
  "LED_COLOR_WAITING": [0, 50, 100],
  "TELEMETRY_EVENT": "telemetry",
  "LED_COLOR_FAILURE": [255, 0, 0],
  "WHITELIST": ["86-225-141-90"],

    "BUZZER_GPIO": 35,
    "SPI_SCK_GPIO": 0,
    "SPI_MOSI_GPIO": 2,
    "SPI_MISO_GPIO": 1,
    "NFC_CS_GPIO": 3,
    "LED_GPIO": 34,
    "MANAGE_WHITELIST_UPDATE": "update",

    "ETH_MDC": 23,
    "ETH_MDIO": 18,
    "ETH_TYPE": "LAN8720",
    "ETH_CLK_MODE": "GPIO0_IN",
    
    "ETH_POWER": 12,
    "ETH_PHY_ADDR": 1,

    "PREFERED_NETWORK": "wifi"  
}






def connect_wifi(SSID='prohidna', password='12345678', log=print):
    import network # type: ignore
    log(f"WIFI: Connecting to WiFi SSID: {SSID}")

    try: 
        sta_if = network.WLAN(network.STA_IF)
        if not sta_if.isconnected():
            sta_if.active(True)
            sta_if.connect(SSID, password)
            while not sta_if.isconnected():
                pass # wait till connection
    except Exception as e:
        log(f"WIFI: Connection error: {e}")
        return None
    log(f"WIFI: Connected, network config: {sta_if.ifconfig()}")
    return sta_if.ifconfig()

def load_credentials(log=print):
    import ujson
    try:
        with open('secrets.json', 'r') as f:
            log("Credentials loaded from secrets.json")
            return ujson.load(f)
    except Exception as e:
        log(f"Error loading credentials: {e}. Maybe the file is missing or corrupted.")
        return {}

def connect_ethernet(mdc = 23, mdio = 18, phy_type = None, phy_addr = 0, log=print):
    import network # type: ignore
    from machine import Pin
    import time

    log("ETHERNET: Setting up Ethernet connection")

    try:
        phy_power = Pin(12, Pin.OUT)
        phy_power.value(1)
        time.sleep_ms(100)

        phy_type = network.PHY_LAN8720

        lan = network.LAN(mdc=Pin(mdc), mdio=Pin(mdio), phy_type=phy_type, phy_addr=phy_addr)
        lan.active(True)

        max_wait = 20

        while not lan.isconnected() and max_wait > 0:
            import time
            time.sleep(0.5)
            max_wait -= 1

        if lan.isconnected():
            log(f"ETHERNET: Connected, network config: {lan.ifconfig()}")
            return lan.ifconfig()
        else:
            log("ETHERNET: Connection timed out")
            return None
    except Exception as e:  
        log(f"ETHERNET: Connection error: {e}")
        return None

def connect(mode, config, credits, log=print):
    try:
        if mode == 'wifi':
            r = connect_wifi(credits.get('WIFI_SSID', 'prohidna'), credits.get('WIFI_PASSWORD', '12345678'))
            if r:
                return r
            else:
                log("Falling back to Ethernet...")
                return connect_ethernet(
                    mdc = config.get('ETH_MDC', 23),
                    mdio = config.get('ETH_MDIO', 18),
                    phy_type = config.get('ETH_PHY_TYPE', None),
                    phy_addr = config.get('ETH_PHY_ADDR', 0),
                    log=log
                )
        elif mode == 'ethernet': 
            r = connect_ethernet(
                mdc = config.get('ETH_MDC', 23),
                mdio = config.get('ETH_MDIO', 18),
                phy_type = config.get('ETH_PHY_TYPE', None),
                phy_addr = config.get('ETH_PHY_ADDR', 0),
                log=log
            )   
            if r:
               return r
            else:
                log("Falling back to WiFi...")
                return connect_wifi(credits.get('WIFI_SSID', 'prohidna'), credits.get('WIFI_PASSWORD', '12345678'), log=log)
    except Exception as e:
        log(f"Connection error: {e}")
        return None

def save_config(config, config_file='config.json', log=print):
    import ujson
    try:
        with open(config_file,'w')as f:ujson.dump(config,f);log("Config saved.")
    except Exception as e:log(f"Config save error:{e}")

def load_config(config, config_file='config.json', log=print):
    import ujson

    try:
        with open(config_file,'r')as f:config=DEFAULT_CONFIG.copy();config.update(ujson.load(f))
        log("Config loaded.")
        if config["READER_ID_AFFIX"]=="unidentified_reader":config["READER_ID_AFFIX"]=generate_default_reader_id();save_config();log(f"Generated UID:{config['READER_ID_AFFIX']}")
    except Exception as e:log(f"Config load error:{e}.Using defaults.");config=DEFAULT_CONFIG.copy();save_config()
