#pragma once
#include <Arduino.h>
#include <Adafruit_NeoPixel.h>

class Led {
    public:
        int led_pin;
        int led_num;
        Adafruit_NeoPixel strip;

        int freq = 60;

        Led(int pin, int num) : led_pin(pin), led_num(num) {
            strip = Adafruit_NeoPixel(num, pin, NEO_GRB + NEO_KHZ800);
        }

        void setup() {
            strip.begin();
            strip.clear();
            strip.show();
        }

        void spin() {
            for (int i = 0; i < led_num; i++) {
                strip.setPixelColor(i, strip.Color(0, 0, 255));
                strip.show();
                delay(50);
                strip.clear();
                strip.show(); // Add this to actually turn off the LEDs
            }
        }
};