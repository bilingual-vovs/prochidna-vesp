# mqtt_manager.py

import uasyncio as asyncio
from umqtt.simple import MQTTClient # type: ignore
import ujson
import time
import re 
from utils import load_credentials

class MqttManager:
    def __init__(self, config, config_cb, reset_cb, db_controller):
        """
        Initializes the MQTT Manager.
        :param config: The main application's configuration dictionary.

        :param config_cb: Callback function to handle configuration updates.
        :param reset_cb: Callback function to trigger a device reset.
        """
        self.config = config
        self.config_callback = config_cb
        self.reset_callback = reset_cb

        self._credentials = load_credentials()

        self.client_id = self._credentials['CLIENT_ID']
        self.broker = self._credentials['BROKER_ADDR']
        self.port = self._credentials['BROKER_PORT']
        self.mqttc = MQTTClient(self.client_id, 
                                self.broker, 
                                user=self._credentials['CLIENT_NAME'],
                                password=self._credentials['MQTT_PASSWORD'],
                                port=self.port,
                                keepalive=12000)
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

        self.last_mqtt_connection = float('inf')

        self.publishing = set()
        self.published = set()
        self.db = db_controller

        self.running = False

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
        while retries < self.config["CONNECTION_RETRIES"]:  # Indicate connection attempt
            try:
                self.log(f"Attempting to connect to broker at {self.broker}...")
                self.mqttc.connect(clean_session=True)

                #  ---------------- INDEV SOLUTION, NEEDS TO BE CHANGED WHEN PRODUCTION BROCKER WILL BE AWAIBLE ----------------
                
                self.mqttc.subscribe(self.topic_whitelist + "#", qos=0)
                self.log(f"Subscribed to whitelist topic: {self.topic_whitelist}")
                self.mqttc.subscribe(f"{self.topic_config_base}/#", qos=0)
                self.log(f"Subscribed to config topic: {self.topic_config_base}/#")
                self.mqttc.subscribe(self.topic_reset, qos=0)
                self.log(f"Subscribed to reset topic: {self.topic_reset}")
                
                self.mqttc.set_last_will(topic=self.topic_offline, msg=self.client_id, retain=True, qos=0)
                self.mqttc.publish(self.topic_online, self.client_id, retain=True, qos=0)
                
                self.log("Successfully connected to MQTT Broker.")
                self.is_connected = True
                return True
            except Exception as e:
                self.log(f"Connection failed: {e}. Retrying...")
                retries += 1
                await asyncio.sleep(self.config["MQTT_RECONNECT_DELAY"])
        
        self.log("Failed to connect after multiple retries.")
        self.reset_callback()
        return False

    async def message_loop(self):
        """Asynchronous task to check for messages and handle reconnection."""
        while self.running:
            try:
                if self.is_connected:
                    self.mqttc.check_msg()
                    self.last_mqtt_connection = time.time
                else:
                    self.log("Connection lost. Attempting to reconnect...")
                    await self.connect()
                await asyncio.sleep_ms(self.config["MQTT_DELAY"])
            except Exception as e:
                self.log(f"Error in message_loop: {e}")
                self.is_connected = False # Trigger reconnect on next iteration

    async def publishing_loop(self):
        while self.running:
            await asyncio.sleep_ms(500)
            if self.is_connected:
                if self.published:
                    await self.db.remove_record(self.published.pop())
                
                try:
                    read = await self.db.get_record(self.publishing)
                    if not read: continue
                    self.publishing.add(read["dec"])
                    if self.register_read(read["dec"], read["fourth"], read['time']): 
                        if read['dec'] in self.publishing: self.publishing.remove(read["dec"])
                        try:
                            if not await self.db.remove_record(read["dec"]): self.published.add(read["dec"])
                        except Exception as e:
                            self.log(f'Error while: removing record: {e}')
                except Exception as e:
                    self.log(f"Error while getting record: {e}")
                        

    def publish(self, topic, message):
        if not self.is_connected:
            return False
        try:
            self.mqttc.publish(topic, str(message), qos=1)
            self.log(f"Published to {topic}: {message}")
            return True
        except Exception as e:
            self.log(f"Failed to publish: {e}")
            self.is_connected = False
            return False
        
    def register_read(self, dec, fourth, time):
        self.publishing.add(dec)
        if self.publish(self.topic_read, {
                "dec": dec,
                "fourth": fourth,
                "time": time
            }): 
            self.publishing.remove(dec)
            try: 
                if self.db.remove_record(dec): return True
                else: self.published.add(dec)
            except Exception as e:
                self.log(f"Error while publishing: {e}")
                self.published.add(dec)
            return True
        return False
        

    def register_error(self, error_message):
        self.publish(self.topic_error, error_message)

    def disconnect(self):
        self.running = False
        if self.is_connected:
            self.log("Disconnecting from MQTT.")
            try:
                self.mqttc.publish(self.topic_offline, self.client_id, retain=True, qos=0)
                self.mqttc.disconnect()
            except Exception as e:
                self.log(f"Error during disconnect: {e}")
        self.is_connected = False

    async def run(self):
        if not await self.connect():
            self.log("MQTT connection is not established, continuing without it...")
            return False
        self.running = True
        asyncio.create_task(self.message_loop())
        asyncio.create_task(self.publishing_loop())
        self.log("Mqtt ready")
        
