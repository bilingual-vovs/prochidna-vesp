import uasyncio as asyncio
from machine import Pin, SPI
import NFC_PN532 as nfc  # type: ignore
import time

class PN532Controller:
    """
    Controller class for handling PN532 NFC reader operations.
    Manages NFC reading, status indication, and database interactions.
    """
    def __init__(self, config, led_controller, db_controller, mqtt_manager):
        """
        Initialize the PN532 controller
        :param config: Application configuration dictionary
        :param led_controller: LED controller instance for status indication
        :param db_controller: Database controller for storing card reads
        :param mqtt_callback: Callback function to notify MQTT about card reads
        """
        self.config = config
        self.led_controller = led_controller
        self.db_controller = db_controller
        self.mqtt_manager = mqtt_manager
        
        # Initialize hardware
        self.spi_dev = SPI(1, 
                          baudrate=1000000,
                          sck=Pin(config['SPI_SCK_GPIO']),
                          mosi=Pin(config['SPI_MOSI_GPIO']),
                          miso=Pin(config['SPI_MISO_GPIO']))
        self.cs = Pin(config['NFC_CS_GPIO'], Pin.OUT, value=1)
        
        # Initialize state
        self.pn532 = None
        self.connected = False
        self.last_uid = None
        
        self.running = False
        self.log("Controller initialized")

    def log(self, message):
        """Logging helper"""
        print(f"[{time.time()}] PN532: {message}")

    async def connect(self):
        """
        Establish connection with the PN532 device.
        Returns True if connection successful, False otherwise.
        """
        if self.pn532 is None:
            self.pn532 = nfc.PN532(self.spi_dev, self.cs)
        
        retries = 0
        while retries < self.config["CONNECTION_RETRIES"]:
            self.led_controller.set_annimation('loading')
            try:
                ic, ver, rev, support = self.pn532.get_firmware_version()
                self.log(f'Found PN532 with firmware version: {ver}.{rev}')
                self.pn532.SAM_configuration()
                self.connected = True
                self.led_controller.set_annimation('waiting')
                return True
            except Exception as e:
                self.log(f"Error connecting to PN532: {e}. Retrying...")
                retries += 1
                await asyncio.sleep(1)
        
        self.log("Failed to connect to PN532 after multiple retries")
        # ADD MQTT ERROR LOGGING
        self.connected = False
        return False

    async def check_connection(self):
        """
        Periodic task to monitor PN532 connection status
        """
        while self.running:
            await asyncio.sleep(self.config["CONNECTION_CHECK_INTERVAL"])
            if not self.connected:
                self.log("PN532 connection is down. Attempting to reconnect.")
                await self.connect()
            else:
                try:
                    # Simple test to verify connection
                    self.pn532.get_firmware_version()
                except Exception as e:
                    self.log(f"Lost connection to PN532: {e}")
                    self.connected = False
                    self.led_controller.set_annimation('loading')

    async def read_cards(self):
        """
        Main task for reading NFC cards
        """
        while self.running:
            if self.connected:
                try:
                    # Try to detect a card
                    uid = self.pn532.read_passive_target(timeout=self.config["NFC_READ_TIMEOUT"])
                    if uid is not None:
                        
                        fourth = nfc.read_card_code_from_block4(self.pn532, uid)
                        uid_string = '-'.join([str(i) for i in uid])

                        if uid_string != self.last_uid:
                            self.last_uid = uid_string
                            self.log(f"Card detected: {uid_string}, with code form fourth block: {fourth}")
                            
                            # Record the read in database
                            timestamp = time.time()
                            self.db_controller.add_record(
                                dec=int(uid_string, 16),  # decimal representation
                                fourth=int(uid_string[-8:], 16) if len(uid_string) >= 8 else 0,  # last 4 bytes
                                time=timestamp
                            )
                            self.mqtt_manager.register_read(
                                dec=int(uid_string, 16),  # decimal representation
                                fourth=int(uid_string[-8:], 16) if len(uid_string) >= 8 else 0,  # last 4 bytes
                                time=timestamp
                            )
                            
                            self.led_controller.set_annimation('success', 0.7)
        
                            # MAYBE ADD IMIDIATE MQTT PROCESSING
                    else:
                        self.last_uid = None  # Reset last UID if no card present
                        
                except Exception as e:
                    self.log(f"Error reading card: {e}")
                    self.connected = False
                    
            await asyncio.sleep(0.1)  # Small delay to prevent tight loop

    async def run(self):
        """
        Start the PN532 controller tasks
        """
        self.running = True
        self.log("Starting PN532 controller tasks")
        
        # Initial connection
        if not await self.connect():
            self.log("Initial connection failed")
            self.led_controller.set_annimation("failure", 10)
            self.stop()
            return False
            
        
        # Start background tasks
        asyncio.create_task(self.check_connection())
        asyncio.create_task(self.read_cards())
        return True

    def stop(self):
        """
        Stop the PN532 controller and cleanup
        """
        self.log("Stopping PN532 controller")
        self.running = False
        self.connected = False
