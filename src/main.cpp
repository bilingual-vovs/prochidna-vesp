#include <Arduino.h>
#include "nfc.h"
#include "network.h"
#include "led.h"

#define PN532_SCK  18
#define PN532_MISO 19
#define PN532_MOSI 23
#define PN532_SS   5 

// Create an instance of the PN532 class
Nfc nfc(PN532_SCK, PN532_MISO, PN532_MOSI, PN532_SS);
Led led(4, 24);

void setup() {
  Serial.begin(115200);
  led.setup();
  initWiFi();
  nfc.setup();

  xTaskCreate(
    [](void*){
      led.ledTask(nullptr);
    }, 
    "LED Task", 
    2048, 
    nullptr, 
    1, 
    nullptr
  );

  xTaskCreate(
    [](void*){
      nfc.readTask(nullptr);
    }, 
    "NFC Task", 
    4096, 
    nullptr, 
    1, 
    nullptr
  );
}

void loop() {

}