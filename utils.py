def generate_default_reader_id():
    """Generates a default reader ID based on the MAC address."""
    import network, binascii # type: ignore
    wlan = network.WLAN(network.STA_IF)
    mac = wlan.config('mac')
    mac_str = binascii.hexlify(mac).decode('utf-8')
    return 'unidentified_reader/' + mac_str


def connect_wifi(SSID='prohidna', password='12345678'):
    import network # type: ignore
    sta_if = network.WLAN(network.STA_IF)
    if not sta_if.isconnected():
        sta_if.active(True)
        sta_if.connect(SSID, password)
        while not sta_if.isconnected():
            pass # wait till connection
    return sta_if.ifconfig()

def load_credentials():
    import ujson
    try:
        with open('secrets.json', 'r') as f:
            return ujson.load(f)
    except Exception as e:
        print(f"Error loading credentials: {e}. Maybe the file is missing or corrupted.")
        return {}

def connect_ethernet(mdc = 23, mdio = 18, phy_type = None, phy_addr = 0):
    import network # type: ignore
    from machine import Pin
    import time

    phy_power = Pin(12, Pin.OUT)
    phy_power.value(1)
    time.sleep_ms(100)

    if phy_type is None:
        phy_type = network.PHY_LAN8720
    else: 
        phy_type = network[phy_type]

    phy_type = network.PHY_LAN8720
    
    lan = network.LAN(mdc=Pin(mdc), mdio=Pin(mdio), phy_type=phy_type, phy_addr=phy_addr)
    lan.active(True)

    max_wait = 20

    while not lan.isconnected() and max_wait > 0:
        import time
        time.sleep(1)
        max_wait -= 1

    if lan.isconnected():
        return lan.ifconfig()
    else:
        raise RuntimeError("Ethernet connection failed")

def connect(mode, config, credits):
    try:
        if mode == 'wifi':
            return connect_wifi(credits.get('WIFI_SSID', 'prohidna'), credits.get('WIFI_PASSWORD', '12345678'))
        elif mode == 'ethernet': 
            return connect_ethernet(
                mdc = config.get('ETH_MDC', 23),
                mdio = config.get('ETH_MDIO', 18),
                phy_type = config.get('ETH_PHY_TYPE', None),
                phy_addr = config.get('ETH_PHY_ADDR', 0)
            )   
    except Exception as e:
        print(f"Error connecting to {mode}: {e}")
        if mode == 'wifi':
            print("Falling back to Ethernet...")
            try:
                return connect_ethernet(
                    mdc = config.get('ETH_MDC', 23),
                    mdio = config.get('ETH_MDIO', 18),
                    phy_type = config.get('ETH_PHY_TYPE', None),
                    phy_addr = config.get('ETH_PHY_ADDR', 0)
                )   
            except Exception as e:
                print(f"Error connecting to ethernet: {e}")
        elif mode == 'ethernet':
            print("Falling back to WiFi...")
            try:
                return connect_wifi(credits.get('WIFI_SSID', 'prohidna'), credits.get('WIFI_PASSWORD', '12345678'))
            except Exception as e:
                print(f"Error connecting to wifi: {e}")
        return None