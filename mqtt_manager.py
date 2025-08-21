# mqtt_manager.py

import uasyncio
from umqtt.simple import MQTTClient
import ujson
import time

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

        self.client_id = config['READER_ID_AFFIX']
        self.broker = config['BROKER_ADDR']
        self.mqttc = MQTTClient(self.client_id, self.broker, keepalive=120)
        self.mqttc.set_callback(self._callback)
        self.is_connected = False
        
        # Define topics for easy access
        self.topic_whitelist = f"{self.client_id}/{config['WHITELIST_TOPIC_SUFFIX']}"
        self.topic_config_base = f"{self.client_id}/{config['CONFIG_TOPIC_SUFFIX']}"
        self.topic_reset = f"{self.client_id}/{config['RESET_TOPIC_SUFFIX']}"
        self.topic_online = f"online/{self.client_id}"
        self.topic_offline = f"offline/{self.client_id}"

    def log(self, message):
        print(f"[{time.time()}] MQTT: {message}")

    def _callback(self, topic_bytes, msg_bytes):
        topic = topic_bytes.decode('utf-8')
        msg = msg_bytes.decode('utf-8')
        self.log(f"Received message on topic: {topic}")

        if topic == self.topic_whitelist:
            try:
                new_whitelist = ujson.loads(msg)
                if isinstance(new_whitelist, list):
                    self.whitelist_callback(new_whitelist)
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
                self.mqttc.connect()
                
                self.mqttc.subscribe(self.topic_whitelist)
                self.mqttc.subscribe(f"{self.topic_config_base}/#")
                self.mqttc.subscribe(self.topic_reset)
                
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

    def publish(self, topic_suffix, message):
        if not self.is_connected:
            return False
        try:
            topic = f"{topic_suffix}/{self.client_id}"
            self.mqttc.publish(topic, str(message))
            self.log(f"Published to {topic}: {message}")
            return True
        except Exception as e:
            self.log(f"Failed to publish: {e}")
            self.is_connected = False
            return False

    def disconnect(self):
        if self.is_connected:
            self.log("Disconnecting from MQTT.")
            try:
                self.mqttc.publish(self.topic_offline, self.client_id, retain=True, qos=1)
                self.mqttc.disconnect()
            except Exception as e:
                self.log(f"Error during disconnect: {e}")
        self.is_connected = False