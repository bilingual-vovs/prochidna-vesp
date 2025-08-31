import network
import time
from machine import Pin

print("Initializing Ethernet with correct clock mode...")

# Крок 1: Вмикаємо живлення для PHY-чіпа
phy_power = Pin(12, Pin.OUT)
phy_power.value(1)
time.sleep_ms(100)

try:
    # Крок 2: Ініціалізуємо LAN з усіма параметрами для Olimex ESP32-POE
    lan = network.LAN(
        mdc=Pin(23), 
        mdio=Pin(18), 
        phy_type=network.PHY_LAN8720, 
        phy_addr=0,
    )

    lan.active(True)

    print("Waiting for connection...")
    max_wait = 20
    while not lan.isconnected() and max_wait > 0:
        time.sleep(1)
        max_wait -= 1

    if lan.isconnected():
        print("✅ Ethernet connected successfully!")
        print(f"IP info: {lan.ifconfig()}")
    else:
        print("❌ Connection failed. Please check your LAN cable and network.")

except Exception as e:
    print(f"Error during Ethernet initialization: {e}")
    print("If the error persists, check your MicroPython firmware version or board revision.")