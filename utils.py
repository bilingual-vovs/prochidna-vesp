def generate_default_reader_id():
    """Generates a default reader ID based on the MAC address."""
    import network, binascii # type: ignore
    wlan = network.WLAN(network.STA_IF)
    mac = wlan.config('mac')
    mac_str = binascii.hexlify(mac).decode('utf-8')
    return 'unidentified_reader/' + mac_str

DEFAULT_CONFIG = {
    # All your config keys remain here...
    "CONNECTION_CHECK_INTERVAL": 5,"CONNECTION_RETRIES": 5,"MQTT_RECONNECT_DELAY": 5,"NFC_READ_TIMEOUT": 300,"MAX_QUEUE_SIZE": 50, "MQTT_DELAY": 500,
    "READER_ID_AFFIX": generate_default_reader_id(),
    "BUZZER_GPIO": 4,"SPI_SCK_GPIO": 18,"SPI_MOSI_GPIO": 23,"SPI_MISO_GPIO": 19,"NFC_CS_GPIO": 5,"LED_GPIO": 32,
    "APROVAL_MELODY": [[659, 150], [698, 150], [784, 150], [880, 300]],
    "DENIAL_MELODY": [[523, 200], [440, 200], [349, 300]],
    "WHITELIST": [],"LED_DIODS_AM": 24,'LED_COLOR_SUCCESS': [0, 255, 0],'LED_COLOR_FAILURE': [255, 0, 0],'LED_COLOR_LOADING': [0, 100, 200],'LED_COLOR_WAITING': [0, 50, 100],'LED_COLOR_OFF': [0, 0, 0],'LED_LOADING_POS': 0,'LED_WAITING_PULSE_ANGLE': 0,'LED_WAITING_PULSE_SPEED': 0.04,
    
    "MQTT_NAMING_TEMPLATE_SUBSCRIBE": "device/$READER_ID_AFFIX/manage/#",
    "MQTT_NAMING_TEMPLATE_PUBLISH": "device/$READER_ID_AFFIX/events/#",
    
    "READ_EVENT": "read",
    "ERROR_EVENT": "error",
    "ONLINE_EVENT": "online",
    "OFFLINE_EVENT": "offline",
    "TELEMETRY_EVENT": "telemetry",

    "MANAGE_WHITELIST": "whitelist/#",
    "MANAGE_WHITELIST_ADD": "add",
    "MANAGE_WHITELIST_REMOVE": "remove",
    "MANAGE_WHITELIST_UPDATE": "update",
    "MANAGE_CONFIG": "configure",
    "MANAGE_RESET": "reset",

    "ETH_MDC": 23,
    "ETH_MDIO": 18,
    "ETH_TYPE": "LAN8720",
    "ETH_CLK_MODE": "GPIO0_IN",
    "ETH_POWER": 12,
    "ETH_PHY_ADDR": 1,

    "PREFERED_NETWORK": "ethernet"  # Options: "wifi", "ethernet"
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
