#include <Arduino.h>
#include <WiFi.h>

const char* ssid = "s5";
const char* password = "opelvectra";

void initWiFi(int retries=10) {
  if (WiFi.status() == WL_CONNECTED and WiFi.SSID() != ssid){
    Serial.println("Already connected to another WiFi");
    WiFi.disconnect();
    delay(200);
  }
  else if (WiFi.status() == WL_CONNECTED and WiFi.SSID() == ssid){
    Serial.println("Already connected to WiFi");
    Serial.println(WiFi.localIP());
    return;
  }
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi ..");
  while (WiFi.status() != WL_CONNECTED and retries-- > 0) {
    Serial.print('.');
    delay(200);
  }
  Serial.println("");
  Serial.println(WiFi.localIP());
}
