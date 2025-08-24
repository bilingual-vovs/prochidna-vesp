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