import NFC_PN532 as nfc
from machine import Pin, SPI, reset
import time
from utils import blink
from umqtt.simple import MQTTClient

connection_check_interval = 5
connection_retries = 15
connection_retries_counter = 0

spi_dev = SPI(1, baudrate=1000000, sck=Pin(18), mosi=Pin(23), miso=Pin(19))


cs = Pin(5, Pin.OUT, value=1)

# --- PN532 Initialization and Reconnection ---
pn532 = None
connected = False

def connect_to_pn532():

    global pn532, connected, connection_retries_counter, connection_retries
    
    if pn532 is None:
        pn532 = nfc.PN532(spi_dev, cs)

    try:
        ic, ver, rev, support = pn532.get_firmware_version()
        print('PN532 found, firmware version: {0}.{1}'.format(ver, rev))
        pn532.SAM_configuration()
        connected = True
        return True
    except RuntimeError as e:
        print(f"Error connecting to PN532: {e}. Retrying connection..." + str(connection_retries_counter))
        if connection_retries_counter >= connection_retries:
            reset()
        connection_retries_counter += 1
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

def publish_read(uid, mqttc):
    mqttc.publish('read', str(uid))



print("Attempting initial connection to PN532...")
while not connected:
    connect_to_pn532()
    if not connected:
        time.sleep(1) 

# --- NFC Reading Logic ---
last_uid = None

def read_nfc(dev, tmot):
    global last_uid, connected, mqttc, connection_retries_counter

    if not connected:
        print(f"PN532 is currently disconnected. Attempting to restore connection before reading... {connection_retries_counter}")
        if not check_pn532_connection():
            if connection_retries_counter >= connection_retries:
                print(f"Failed to restore PN532 connection after {connection_retries} retries. Initiating system reset.")
                reset() # Triggers system reboot
            connection_retries_counter += 1
            return False 
    connection_retries_counter = 0 # Reset counter only if connection is confirmed active

    try:
        uid = dev.read_passive_target(timeout=tmot)
        if uid is not None:
            if uid != last_uid:
                last_uid = uid
                uid_str_hex = '-'.join(['{:02X}'.format(i) for i in uid])
                uid_str_dec = '-'.join([str(i) for i in uid])

                blink(3, delay_ms=30)
                # Ensure MQTT connection is still active before publishing
                try:
                    mqttc.ping() # Check if MQTT connection is alive
                except Exception as mqtt_e:
                    print(f"MQTT connection lost during ping: {mqtt_e}. Reconnecting MQTT.")
                    try:
                        mqttc.connect() # Reconnect MQTT
                        print("MQTT reconnected successfully.")
                    except Exception as reconnect_e:
                        print(f"Failed to reconnect MQTT: {reconnect_e}.")
                        # Decide if you want to reset here or just continue without MQTT
                        # For example, if MQTT is critical:
                        # reset() 
                        return False # Don't publish if MQTT is down

                publish_read(uid_str_dec, mqttc)

                print("")
                print('--- Card Found! ---')
                print('UID (hexadecimal):', uid_str_hex)
                print('UID (decimal):', uid_str_dec)
                print('--------------------')
                return True
        return False 
    except RuntimeError as e: # Catch communication errors specifically from PN532 library
        print(f"PN532 communication error (RuntimeError): {e}. Module disconnected.")
        connected = False 
        return False
    except OSError as e: # Catch OS-level errors like ENOTCONN (Errno 128)
        # This is where your [Errno 128] ENOTCONN is being caught.
        print(f"PN532 underlying communication (OSError): {e}. Module disconnected.")
        connected = False
        return False
    except Exception as e: # Catch any other unexpected errors
        print(f"Unexpected general error while reading: {e}. Module disconnected.")
        connected = False
        return False

# --- Main Program Loop ---
print('Waiting for RFID cards...')
check_counter = 0
while True:
    read_nfc(pn532, 500)
    
    check_counter += 1
    if check_counter >= connection_check_interval:
        
        check_pn532_connection() 
        check_counter = 0 

    time.sleep(0.1) 