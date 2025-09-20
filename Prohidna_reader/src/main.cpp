#include <Arduino.h>
#include <led.h>

#define LED_PIN 4
#define LED_COUNT 24

Led led(LED_PIN, LED_COUNT);

void setup() {
  Serial.begin(115200);
  Serial.println("NeoPixel Individual LED Control Test");
  led.setup();
// Initialize all pixels to 'off'
}

void loop() {
  led.iteration();
}
