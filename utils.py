def blink(times, delay_ms=100):
    import machine
    import time 
    pin = machine.Pin(2, machine.Pin.OUT)

    for _ in range(times):
        pin.value(1) 
        time.sleep_ms(delay_ms)
        pin.value(0) 
        time.sleep_ms(delay_ms)

def generate_default_reader_id():
    """Generates a default reader ID based on the MAC address."""
    import network, binascii
    wlan = network.WLAN(network.STA_IF)
    mac = wlan.config('mac')
    mac_str = binascii.hexlify(mac).decode('utf-8')
    return 'unidentified_reader/' + mac_str