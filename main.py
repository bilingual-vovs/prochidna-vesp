import NFC_PN532 as nfc
from machine import Pin, SPI, reset
import time
import uasyncio as asyncio
from utils import blink
from umqtt.simple import MQTTClient

# --- Configuration ---
CONNECTION_CHECK_INTERVAL = 5
CONNECTION_RETRIES = 5
CLIENT_NAME = 'blue'
BROKER_ADDR = '192.168.232.73'
MQTT_RECONNECT_DELAY = 5
NFC_READ_TIMEOUT = 500
DATA_PUBLISH_TOPIC = 'read'
MAX_QUEUE_SIZE = 10  # Maximum size of the data queue

# --- Hardware Setup ---
spi_dev = SPI(1, baudrate=1000000, sck=Pin(18), mosi=Pin(23), miso=Pin(19))
cs = Pin(5, Pin.OUT, value=1)

# --- Global State ---
pn532 = None
mqttc = None
connected_nfc = False
connected_mqtt = False
last_uid = None
data_queue = []  # Use a list as a queue
queue_lock = asyncio.Lock()  # Use a lock to protect the queue

# --- Helper Functions ---

def log(message):
    print(f"[{time.time()}] {message}")

# --- NFC Functions ---

async def connect_to_pn532():
    global pn532, connected_nfc
    if pn532 is None:
        pn532 = nfc.PN532(spi_dev, cs)
    retries = 0
    while retries < CONNECTION_RETRIES:
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
    global connected_nfc
    while True:
        await asyncio.sleep(CONNECTION_CHECK_INTERVAL)
        if not connected_nfc:
            log("PN532 connection is down. Attempting to reconnect.")
            await connect_to_pn532()
        else:
            try:
                ic, ver, rev, support = pn532.get_firmware_version()
            except Exception as e:
                log(f"PN532 connection lost: {e}")
                connected_nfc = False

async def read_nfc():
    global last_uid, connected_nfc, data_queue, queue_lock

    while True:
        if connected_nfc:
            try:
                uid = pn532.read_passive_target(timeout=NFC_READ_TIMEOUT)
                if uid is not None:
                    uid_str_hex = '-'.join(['{:02X}'.format(i) for i in uid])
                    uid_str_dec = '-'.join([str(i) for i in uid])

                    if uid != last_uid:
                        last_uid = uid
                        log(f"Card Found! UID (hexadecimal): {uid_str_hex}, UID (decimal): {uid_str_dec}")

                        async with queue_lock:  # Acquire the lock before modifying the queue
                            if len(data_queue) < MAX_QUEUE_SIZE:
                                data_queue.append(uid_str_dec)
                                blink(3, delay_ms=30)
                            else:
                                log("Data queue is full. Discarding data.") # Handle overflow
            except Exception as e:
                log(f"Error reading NFC: {e}")
                connected_nfc = False
        await asyncio.sleep(0.1)

# --- MQTT Functions ---

async def mqtt_connect():
    global mqttc, connected_mqtt
    mqttc = MQTTClient(CLIENT_NAME, BROKER_ADDR, keepalive=60)
    retries = 0
    while retries < CONNECTION_RETRIES:
        try:
            mqttc.connect()
            log("Connected to MQTT Broker")
            connected_mqtt = True
            return True
        except Exception as e:
            log(f"MQTT Connection failed: {e}, retrying in {MQTT_RECONNECT_DELAY} seconds...")
            retries += 1
            await asyncio.sleep(MQTT_RECONNECT_DELAY)
    log("Failed to connect to MQTT after multiple retries.")
    return False

async def check_mqtt_connection():
    global connected_mqtt
    while True:
        await asyncio.sleep(CONNECTION_CHECK_INTERVAL)
        if not connected_mqtt:
            log("MQTT connection is down. Attempting to reconnect.")
            await mqtt_connect()
        else:
            try:
                mqttc.ping()
            except Exception as e:
                log(f"MQTT connection lost: {e}")
                connected_mqtt = False


async def publish_data():
    global connected_mqtt, data_queue, queue_lock
    while True:
        if connected_mqtt:
            async with queue_lock:  # Acquire the lock before modifying the queue
                if data_queue:
                    data = data_queue.pop(0)  # Pop from the beginning of the list (FIFO)
                    try:
                        mqttc.publish(DATA_PUBLISH_TOPIC, str(data))
                        log(f"Published data: {data}")
                    except Exception as e:
                        log(f"Error publishing data: {e}")
                        # Consider re-adding the data to the queue if the publish fails
                        data_queue.insert(0, data)  # Add back to the beginning
        await asyncio.sleep(0.1)

# --- Main ---
async def main():

    await connect_to_pn532()
    await mqtt_connect()

    asyncio.create_task(check_pn532_connection())
    asyncio.create_task(check_mqtt_connection())
    asyncio.create_task(read_nfc())
    asyncio.create_task(publish_data())

    while True:
        await asyncio.sleep(1)

# --- Entry Point ---
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("Exiting...")
    finally:
        if pn532:
            log("Releasing NFC resources.")
        if mqttc:
            log("Disconnecting from MQTT.")
            mqttc.disconnect()
        log("Done.")