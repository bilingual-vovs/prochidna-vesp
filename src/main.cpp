#include <Arduino.h>
#include "nfc.h"

#define PN532_SCK  18
#define PN532_MISO 19
#define PN532_MOSI 23
#define PN532_SS   5 

// Create an instance of the PN532 class
Nfc nfc(PN532_SCK, PN532_MISO, PN532_MOSI, PN532_SS);

void setup() {
  Serial.begin(115200);
  nfc.setup();
}

void loop() {
  u_int8_t* r = nfc.read();
  Serial.println("from loop " + String((long)r));
  delay(1000);
}