# mqtt_manager.py

import uasyncio
from umqtt.simple import MQTTClient # type: ignore
import ujson
import time
import re 
from utils import load_credentials

class MqttManager:
    def __init__(self, config, led_cb, whitelist_cb, config_cb, reset_cb):
        """
        Initializes the MQTT Manager.
        :param config: The main application's configuration dictionary.
        :param led_state: The shared state dictionary for LED control.
        :param whitelist_cb: Callback function to handle whitelist updates.
        :param config_cb: Callback function to handle configuration updates.
        :param reset_cb: Callback function to trigger a device reset.
        """
        self.config = config
        self.led_callback = led_cb
        self.whitelist_callback = whitelist_cb
        self.config_callback = config_cb
        self.reset_callback = reset_cb

        self._credentials = load_credentials()

        self.client_id = self._credentials['CLIENT_ID']
        self.broker = self._credentials['BROKER_ADDR']
        self.port = self._credentials.get('BROKER_PORT', 1883)
        self.mqttc = MQTTClient(self.client_id, 
                                self.broker, 
                                user=self._credentials['CLIENT_NAME'],
                                password=self._credentials['MQTT_PASSWORD'],
                                port=self.port,
                                keepalive=120)
        self.mqttc.set_callback(self._callback)
        self.is_connected = False
        
        # Define topics for easy access
        self.topic_whitelist = self.form_topic_sub(config['MANAGE_WHITELIST'])
        self.topic_config_base = self.form_topic_sub(config['MANAGE_CONFIG'])
        self.topic_reset = self.form_topic_sub(config['MANAGE_RESET'])

        self.topic_online = self.form_topic_pub(config["ONLINE_EVENT"])
        self.topic_offline = self.form_topic_pub(config["OFFLINE_EVENT"])
        self.topic_read = self.form_topic_pub(config['READ_EVENT'])
        self.topic_error = self.form_topic_pub(config["ERROR_EVENT"])

        self.whitelist_add = config["MANAGE_WHITELIST_ADD"]
        self.whitelist_remove = config["MANAGE_WHITELIST_REMOVE"]
        self.whitelist_Update = config["MANAGE_WHITELIST_UPDATE"]


    def log(self, message):
        print(f"[{time.time()}] MQTT: {message}")

    def form_topic_sub(self, subtopic):
        r = re.sub(r'\$([A-Z0-9_]+)', lambda m: self.config[m.group(1)], self.config["MQTT_NAMING_TEMPLATE_SUBSCRIBE"])
        return re.sub(r'#', subtopic, r)
    
    def form_topic_pub(self, subtopic):
        r = re.sub(r'\$([A-Z0-9_]+)', lambda m: self.config[m.group(1)], self.config["MQTT_NAMING_TEMPLATE_PUBLISH"])
        return re.sub(r'#', subtopic, r)

    def _callback(self, topic_bytes, msg_bytes):
        topic = topic_bytes.decode('utf-8')
        msg = msg_bytes.decode('utf-8')
        self.log(f"Received message on topic: {topic}")
        if topic.startswith(self.topic_whitelist):
            action = topic.split('/')[-1]
            self.log(f"Whitelist action: {action} with message: {msg}")
            if action == self.whitelist_add:
                try:
                    new_entry = ujson.loads(msg)
                    if isinstance(new_entry, list):
                        self.whitelist_callback("add", new_entry) # Support adding a list of UIDs
                    elif isinstance(new_entry, str):
                        self.whitelist_callback("add", [new_entry]) # Support adding a single UID string
                    else:
                        self.log("Invalid whitelist entry format. Expected a list of UIDs or a single UID string.")
                except Exception as e:
                    self.log(f"Error processing whitelist addition: {e}")
            elif action == self.whitelist_remove:
                try:
                    entry_to_remove = ujson.loads(msg)
                    if isinstance(entry_to_remove, list):
                        self.whitelist_callback("remove", entry_to_remove) # Support removing a list of UIDs
                    elif isinstance(entry_to_remove, str):
                        self.whitelist_callback("remove", [entry_to_remove]) # Support removing a single UID
                    else:
                        self.log("Invalid whitelist entry format. Expected a list of UIDs or a single UID string.")
                except Exception as e:
                    self.log(f"Error processing whitelist removal: {e}")
            elif action == self.whitelist_Update:
                try:
                    new_whitelist = ujson.loads(msg)
                    if isinstance(new_whitelist, list):
                        self.whitelist_callback("update", new_whitelist)
                    else:
                        self.log("Invalid whitelist format. Expected a list.")
                except Exception as e:
                    self.log(f"Error processing whitelist update: {e}")
        
        elif topic.startswith(self.topic_config_base):
            config_var = topic.split('/')[-1]
            self.config_callback(config_var, msg)
            
        elif topic == self.topic_reset:
            self.log("Reset command received. Triggering reset.")
            self.reset_callback()

    async def connect(self):
        retries = 0
        while retries < self.config["CONNECTION_RETRIES"]:
            self.led_callback('waiting', 0)  # Indicate connection attempt
            try:
                self.log(f"Attempting to connect to broker at {self.broker}...")
                self.mqttc.connect(clean_session=True)

                #  ---------------- INDEV SOLUTION, NEEDS TO BE CHANGED WHEN PRODUCTION BROCKER WILL BE AWAIBLE ----------------
                
                self.mqttc.subscribe(self.topic_whitelist + "#", qos=1)
                self.log(f"Subscribed to whitelist topic: {self.topic_whitelist}")
                self.mqttc.subscribe(f"{self.topic_config_base}/#", qos=1)
                self.log(f"Subscribed to config topic: {self.topic_config_base}/#")
                self.mqttc.subscribe(self.topic_reset, qos=1)
                self.log(f"Subscribed to reset topic: {self.topic_reset}")
                
                self.mqttc.set_last_will(topic=self.topic_offline, msg=self.client_id, retain=True, qos=1)
                self.mqttc.publish(self.topic_online, self.client_id, retain=True, qos=1)
                
                self.log("Successfully connected to MQTT Broker.")
                self.is_connected = True
                return True
            except Exception as e:
                self.log(f"Connection failed: {e}. Retrying...")
                retries += 1
                await uasyncio.sleep(self.config["MQTT_RECONNECT_DELAY"])
        
        self.log("Failed to connect after multiple retries.")
        return False

    async def message_loop(self):
        """Asynchronous task to check for messages and handle reconnection."""
        while True:
            try:
                if self.is_connected:
                    self.mqttc.check_msg()
                else:
                    self.log("Connection lost. Attempting to reconnect...")
                    await self.connect()
                await uasyncio.sleep_ms(self.config["MQTT_DELAY"])
            except Exception as e:
                self.log(f"Error in message_loop: {e}")
                self.is_connected = False # Trigger reconnect on next iteration

    def publish(self, topic, message):
        if not self.is_connected:
            return False
        try:
            self.mqttc.publish(topic, str(message))
            self.log(f"Published to {topic}: {message}")
            return True
        except Exception as e:
            self.log(f"Failed to publish: {e}")
            self.is_connected = False
            return False
        
    def register_read(self, data):
        self.publish(self.topic_read, data)

    def register_error(self, error_message):
        self.publish(self.topic_error, error_message)

    def disconnect(self):
        if self.is_connected:
            self.log("Disconnecting from MQTT.")
            try:
                self.mqttc.publish(self.topic_offline, self.client_id, retain=True, qos=1)
                self.mqttc.disconnect()
            except Exception as e:
                self.log(f"Error during disconnect: {e}")
        self.is_connected = False