import NFC_PN532 as nfc
from machine import Pin, SPI
import time
from utils import blink
from umqtt.simple import MQTTClient

spi_dev = SPI(1, baudrate=1000000, sck=Pin(18), mosi=Pin(23), miso=Pin(19))


cs = Pin(5, Pin.OUT, value=1)

# --- PN532 Initialization and Reconnection ---
pn532 = None
connected = False

def connect_to_pn532():

    global pn532, connected
    
    if pn532 is None:
        pn532 = nfc.PN532(spi_dev, cs)

    try:
        ic, ver, rev, support = pn532.get_firmware_version()
        print('PN532 found, firmware version: {0}.{1}'.format(ver, rev))
        pn532.SAM_configuration()
        connected = True
        return True
    except RuntimeError as e:
        print(f"Error connecting to PN532: {e}. Retrying connection...")
        connected = False
        return False

def check_pn532_connection():

    global connected
    if not connected:
        return connect_to_pn532() 

    try:
        
        ic, ver, rev, support = pn532.get_firmware_version()
        
        connected = True
        return True
    except RuntimeError as e:
        print(f"PN532 connection lost during check: {e}. Marking as disconnected.")
        connected = False
        return False
    except Exception as e:
        print(f"An unexpected error occurred during connection check: {e}. Marking as disconnected.")
        connected = False
        return False
    


CLIENT_NAME = 'blue'
BROKER_ADDR = '192.168.31.149'
mqttc = MQTTClient(CLIENT_NAME, BROKER_ADDR, keepalive=60)
mqttc.connect()



print("Attempting initial connection to PN532...")
while not connected:
    connect_to_pn532()
    if not connected:
        time.sleep(2) 

# --- NFC Reading Logic ---
last_uid = None

def read_nfc(dev, tmot):
    global last_uid, connected

    if not connected:
        print("PN532 is currently disconnected. Attempting to restore connection before reading...")
        if not check_pn532_connection(): 
            return False 


    try:
        uid = dev.read_passive_target(timeout=tmot)
        if uid is not None:
            if uid != last_uid:
                last_uid = uid
                uid_str_hex = '-'.join(['{:02X}'.format(i) for i in uid])
                uid_str_dec = '-'.join([str(i) for i in uid])

                blink(3, delay_ms=30)

                print("")
                print('--- Card Found! ---')
                print('UID (hexadecimal):', uid_str_hex)
                print('UID (decimal):', uid_str_dec)
                print('--------------------')
                return True
        return False 
    except RuntimeError as e:
        print(f"Error while reading from PN532: {e}. Module disconnected.")
        connected = False 
        return False
    except Exception as e:
        print(f"Unexpected error while reading: {e}")
        connected = False
        return False

# --- Main Program Loop ---
print('Waiting for RFID cards...')
connection_check_interval = 10 
check_counter = 0

while True:
    read_nfc(pn532, 500)
    
    check_counter += 1
    if check_counter >= connection_check_interval:
        
        check_pn532_connection() 
        check_counter = 0 

    time.sleep(0.1) 