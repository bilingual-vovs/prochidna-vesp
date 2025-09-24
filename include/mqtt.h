// #include <Arduino.h>
// // Required libraries for WiFi and Asynchronous MQTT
// #include <WiFi.h>
// #include "AsyncTCP.h"
// #include "AsyncMQTT_Generic.h"

// // --- WiFi & MQTT Configuration ---
// // Replace with your network credentials
// #define WIFI_SSID "YOUR_WIFI_SSID"
// #define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// // Public MQTT Broker
// #define MQTT_HOST "broker.hivemq.com"
// #define MQTT_PORT 1883

// // MQTT Topics
// #define MQTT_PUB_TOPIC "esp32/test/publish"
// #define MQTT_SUB_TOPIC "esp32/test/subscribe"

// // --- Global Objects ---
// AsyncMqttClient mqttClient;
// unsigned long previousMillis = 0;   // will store last time MQTT message was published

// // --- Callback Functions ---

// void onMqttConnect(bool sessionPresent) {
//   Serial.println("Connected to MQTT broker!");
//   Serial.print("Session present: ");
//   Serial.println(sessionPresent);

//   // Subscribe to the topic
//   uint16_t packetIdSub = mqttClient.subscribe(MQTT_SUB_TOPIC, 1);
//   Serial.print("Subscribing at QoS 1, packetId: ");
//   Serial.println(packetIdSub);

//   // Publish a "connected" message
//   mqttClient.publish(MQTT_PUB_TOPIC, 0, true, "ESP32 Online");
//   Serial.println("Published ESP32 Online message.");
// }

// void onMqttDisconnect(AsyncMqttClientDisconnectReason reason, int16_t code) {
//   Serial.println("Disconnected from MQTT broker.");
//   // For a robust solution, you would add reconnection logic here,
//   // possibly with a timer to avoid spamming connection requests.
//   if (WiFi.isConnected()) {
//     mqttClient.connect();
//   }
// }

// void onMqttSubscribe(uint16_t packetId, uint8_t qos) {
//   Serial.println("Subscribe acknowledged.");
//   Serial.print("  packetId: ");
//   Serial.println(packetId);
//   Serial.print("  qos: ");
//   Serial.println(qos);
// }

// void onMqttMessage(char* topic, char* payload, AsyncMqttClientMessageProperties properties, size_t len, size_t index, size_t total) {
//   Serial.println("--- New Message ---");
//   Serial.print("Topic: ");
//   Serial.println(topic);
  
//   // The payload is not null-terminated, so we create a buffer
//   char payload_buf[len + 1];
//   strncpy(payload_buf, payload, len);
//   payload_buf[len] = '\0';

//   Serial.print("Payload: ");
//   Serial.println(payload_buf);
//   Serial.println("-----------------");
// }

// void onMqttPublish(uint16_t packetId) {
//   Serial.print("Publish acknowledged, packetId: ");
//   Serial.println(packetId);
// }

// void connectToWifi() {
//   Serial.print("Connecting to WiFi...");
//   WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
//   while (WiFi.status() != WL_CONNECTED) {
//     delay(500);
//     Serial.print(".");
//   }
//   Serial.println("\nWiFi connected!");
//   Serial.print("IP address: ");
//   Serial.println(WiFi.localIP());
// }

// // --- Main Program ---

// void setup() {
//   Serial.begin(115200);
//   Serial.println("\nAsync MQTT Client Minimal Example");

//   connectToWifi();

//   // Set up MQTT Callbacks
//   mqttClient.onConnect(onMqttConnect);
//   mqttClient.onDisconnect(onMqttDisconnect);
//   mqttClient.onSubscribe(onMqttSubscribe);
//   mqttClient.onMessage(onMqttMessage);
//   mqttClient.onPublish(onMqttPublish);
  
//   // Set MQTT Server
//   mqttClient.setServer(MQTT_HOST, MQTT_PORT);

//   // Connect to MQTT
//   Serial.println("Connecting to MQTT broker...");
//   mqttClient.connect();
// }

// void loop() {
//   // Publish a message every 10 seconds.
//   // This is a non-blocking way to handle timed events.
//   unsigned long currentMillis = millis();
//   if (currentMillis - previousMillis >= 10000) {
//     previousMillis = currentMillis;

//     // Check if connected before publishing
//     if (mqttClient.connected()) {
//       // Publish a message with a counter
//       static uint32_t counter = 0;
//       char msg[32];
//       snprintf(msg, sizeof(msg), "Hello #%d", counter++);
      
//       uint16_t packetIdPub = mqttClient.publish(MQTT_PUB_TOPIC, 1, true, msg);
//       Serial.printf("Publishing on topic %s at QoS 1, packetId: %i, message: %s\n", MQTT_PUB_TOPIC, packetIdPub, msg);
//     }
//   }
//   // The magic of async is that the loop can be nearly empty or
//   // used for other non-blocking tasks. All MQTT work is handled by callbacks.
// }