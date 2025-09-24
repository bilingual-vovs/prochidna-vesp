#include <Arduino.h>
#include <WiFi.h>
#include "Adafruit_MQTT.h"
#include "Adafruit_MQTT_Client.h"

#include "secrets.h"
// --- Global Objects ---
// Create a WiFiClient object to connect to the MQTT server.
WiFiClient client;

// Setup the MQTT client class by passing in the WiFi client and broker details.
Adafruit_MQTT_Client mqtt(&client, MQTT_SERVER, MQTT_PORT, MQTT_USER, MQTT_PASS);

// --- Setup Feeds (Topics) ---
// Create an object for the topic you want to publish to.
Adafruit_MQTT_Publish prohidna_reads = Adafruit_MQTT_Publish(&mqtt, "prohidna/reads");

// Create an object for the topic you want to subscribe to.
Adafruit_MQTT_Subscribe prohidna_config = Adafruit_MQTT_Subscribe(&mqtt, "prohidna/config");


// Function to connect and reconnect to the MQTT broker.
void MQTT_connect() {
  int8_t ret;

  // Stop if already connected.
  if (mqtt.connected()) {
    return;
  }

  Serial.print("Connecting to MQTT... ");

  uint8_t retries = 3;
  while ((ret = mqtt.connect()) != 0) { // connect will return 0 for success
       Serial.println(mqtt.connectErrorString(ret));
       Serial.println("Retrying MQTT connection in 5 seconds...");
       mqtt.disconnect();
       delay(5000);  // wait 5 seconds
       retries--;
       if (retries == 0) {
         // basically die and wait for WDT to reset me
         while (1);
       }
  }
  Serial.println("MQTT Connected!");
}


void setup() {
  Serial.begin(115200);
  delay(10);

  // Connect to WiFi
  Serial.println("Connecting to WiFi...");
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected!");

  // Setup a function to be called when a message is received on the subscription.
  prohidna_config.setCallback([](char *data, uint16_t len) {
    Serial.print("Message received on 'prohidna/config': ");
    Serial.println(data);
  });

  // Subscribe to the config feed.
  mqtt.subscribe(&prohidna_config);
}


void loop() {
  // Ensure the connection to the MQTT server is alive (this will make reconnects).
  MQTT_connect();

  // This is the MQTT polling function. It must be called regularly to
  // check for incoming messages and handle keep-alives.
  mqtt.processPackets(10); // 10-second timeout for reading packets

  // Ping the server to keep the connection alive.
  if(!mqtt.ping()) {
    mqtt.disconnect();
  }

  // Publish a message every 10 seconds.
  static unsigned long last_pub = 0;
  if (millis() - last_pub > 10000) {
    last_pub = millis();
    char msg[50];
    snprintf(msg, 50, "Read UID_%lu", millis());
    
    // --- THIS IS THE KEY PART ---
    // Publish the message with QoS level 1.
    if (prohidna_reads.publish(msg, 1)) {
      Serial.printf("Successfully published QoS 1 message: %s\n", msg);
    } else {
      Serial.println("Failed to publish QoS 1 message.");
    }
  }
}