# mqtt_manager.py ( rewritten for mqtt_as )

import uasyncio as asyncio
import ujson
import time
import re
from utils import load_credentials
from mqtt_as import MQTTClient, config as mqtt_config

class MqttManager:
    def __init__(self, config, config_cb, reset_cb, whitelist_cb, db_controller):
        """
        Initializes the Asynchronous MQTT Manager.
        """
        self.app_config = config
        self.config_callback = config_cb
        self.reset_callback = reset_cb
        self.whitelist_callback = whitelist_cb
        self.db = db_controller
        self.client = None # MQTTClient will be instantiated in run()
        self.is_connected = False
        self.running = False
        
        # Sets for tracking message state
        self.publishing = set()

        self.client_config = mqtt_config.copy()

        # Load secrets and configure the client
        self._setup_client_config()

    def log(self, message):
        print(f"[{time.time()}] MQTT: {message}")

    def _setup_client_config(self):
        """Loads credentials and prepares the config dict for MQTTClient."""
        credentials = load_credentials(log=self.log)
        
        # ---- Populate the CLIENT_CONFIG dictionary ----
        self.client_config["ssid"] = credentials.get("WIFI_SSID")
        self.client_config["wifi_pw"] = credentials.get("WIFI_PASSWORD")
        self.client_config["server"] = credentials.get("BROKER_ADDR")
        self.client_config["port"] = credentials.get("BROKER_PORT")
        self.client_config["user"] = credentials.get("CLIENT_NAME")
        self.client_config["password"] = credentials.get("MQTT_PASSWORD")
        self.client_config["client_id"] = credentials.get("CLIENT_ID")
        
        # Define Last Will and Testament (LWT)
        topic_offline = self.form_topic_pub(self.app_config["OFFLINE_EVENT"])
        self.client_config["will"] = (topic_offline, credentials.get("CLIENT_ID"), True, 0)
        
        # Set callbacks
        self.client_config["subs_cb"] = self._subscription_callback
        self.client_config["on_up"] = self._on_connect_callback
        self.client_config["on_down"] = self._on_disconnect_callback
        

    def form_topic_sub(self, subtopic):
        r = re.sub(r'\$([A-Z0-9_]+)', lambda m: self.app_config[m.group(1)], self.app_config["MQTT_NAMING_TEMPLATE_SUBSCRIBE"])
        return re.sub(r'#', subtopic, r)
    
    def form_topic_pub(self, subtopic):
        r = re.sub(r'\$([A-Z0-9_]+)', lambda m: self.app_config[m.group(1)], self.app_config["MQTT_NAMING_TEMPLATE_PUBLISH"])
        return re.sub(r'#', subtopic, r)

    # ---- Callback methods for mqtt_as ----
    
    async def _on_connect_callback(self, client):
        """Called when connection to the broker is established."""
        self.log("Successfully connected to MQTT Broker.")
        self.is_connected = True
        
        # Subscribe to topics
        topic_whitelist = self.form_topic_sub(self.app_config['MANAGE_WHITELIST']) + "#"
        topic_config = self.form_topic_sub(self.app_config['MANAGE_CONFIG']) + "/#"
        topic_reset = self.form_topic_sub(self.app_config['MANAGE_RESET'])
        
        await client.subscribe(topic_whitelist, 1)
        self.log(f"Subscribed to: {topic_whitelist}")
        await client.subscribe(topic_config, 1)
        self.log(f"Subscribed to: {topic_config}")
        await client.subscribe(topic_reset, 1)
        self.log(f"Subscribed to: {topic_reset}")
        
        # Publish online message
        topic_online = self.form_topic_pub(self.app_config["ONLINE_EVENT"])
        await self.publish(topic_online, self.client_config["client_id"], retain=True, qos=0)

    def _on_disconnect_callback(self, client):
        """Called when the client disconnects."""
        self.log("Connection to broker lost.")
        self.is_connected = False

    def _subscription_callback(self, topic_bytes, msg_bytes):
        """Handles all incoming subscribed messages."""
        topic = topic_bytes.decode()
        msg = msg_bytes.decode()
        self.log(f"Received on {topic}: {msg}")

        # Define base topics for matching
        topic_whitelist_base = self.form_topic_sub(self.app_config['MANAGE_WHITELIST'])
        topic_config_base = self.form_topic_sub(self.app_config['MANAGE_CONFIG'])
        topic_reset = self.form_topic_sub(self.app_config['MANAGE_RESET'])

        try:
            if topic.startswith(topic_whitelist_base):
                action = topic.split('/')[-1]
                data = ujson.loads(msg)
                # Ensure data is a list for consistent handling
                if isinstance(data, str): data = [data]
                if not isinstance(data, list): raise ValueError("Payload must be a UID string or a list of UIDs")
                self.whitelist_callback(action, data)

            elif topic.startswith(topic_config_base):
                config_var = topic.split('/')[-1]
                self.config_callback(config_var, msg)
                
            elif topic == topic_reset:
                self.log("Reset command received.")
                self.reset_callback()
        except Exception as e:
            self.log(f"Error processing message on topic {topic}: {e}")

    # ---- Core Functionality ----

    async def publish(self, topic, message, retain=False, qos=1, timeout_ms=500):
        if not self.is_connected:
            self.log("Publish failed: Not connected.")
            return False
        try:
            payload = ujson.dumps(message) if isinstance(message, (dict, list)) else str(message)
            # await self.client.publish(topic, payload, retain, qos)
            await asyncio.wait_for(
                self.client.publish(topic, payload, retain, qos),
                timeout_ms / 1000
            )
            # self.log(f"Published to {topic}: {payload}")
            return True
        except asyncio.TimeoutError:
            self.log(f"Failed to publish to {topic}: Timed out after {timeout_ms}ms")
            return False
        except Exception as e:
            self.log(f"Failed to publish to {topic}: {e}")
            return False

    async def publishing_loop(self):
        """Periodically checks DB for records and tries to publish them."""
        self.log("Publishing loop started.")
        while self.running:
            if self.is_connected:
                record = None
                try:
                    # Get the oldest record that is not currently being published
                    record = await self.db.get_record(self.publishing)
                    self.log(record)
                    if record:
                        dec = record["dec"]
                        self.publishing.add(dec) # Mark as "in-flight"
                        
                        # Attempt to publish the record
                        if await self.register_read(dec, record["fourth"], record['time']):
                            await self.db.remove_record(dec)
                        
                        self.publishing.remove(dec) # Unmark
                except Exception as e:
                    self.log(f"Error in publishing_loop: {e}")
                    if record and record.get("dec") in self.publishing:
                        self.publishing.remove(record.get("dec"))
            await asyncio.sleep_ms(500) # Check every 500ms

    async def register_read(self, dec, fourth, time):
        topic_read = self.form_topic_pub(self.app_config['READ_EVENT'])
        message = {"dec": dec, "fourth": fourth, "time": time}
        return await self.publish(topic_read, message, qos=1)
        
    async def register_error(self, error_message):
        topic_error = self.form_topic_pub(self.app_config["ERROR_EVENT"])
        await self.publish(topic_error, error_message, qos=0)

    async def run(self):
        """Starts the MQTT client and the publishing loop task."""
        self.log("Starting MQTT Manager...")
        self.running = True
        MQTTClient.DEBUG = True # Optional: for verbose output from the library
        self.client = MQTTClient(self.client_config)
        asyncio.create_task(self.publishing_loop())
        try:
            # This is a forever-blocking call that handles connection/reconnection
            await self.client.connect()
        except OSError as e:
            self.log(f"MQTT connection failed. Will retry in background. Error: {e}")
        
    def disconnect(self):
        """Gracefully disconnects the client."""
        self.log("Disconnecting from MQTT.")
        self.running = False
        if self.client:
            self.client.close() # The library handles LWT publishing