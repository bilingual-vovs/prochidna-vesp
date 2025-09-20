#pragma once
#include <Arduino.h>
#include <Adafruit_NeoPixel.h>

class Led {
    public:
        int led_pin;
        int led_num;
        Adafruit_NeoPixel strip;

        int freq = 60;
        enum State {waiting, loading};
        enum State animation = loading;
        int a_delay;

        Led(int pin, int num) : led_pin(pin), led_num(num) {
            strip = Adafruit_NeoPixel(num, pin, NEO_GRB + NEO_KHZ800);
        }

        void setup() {
            strip.begin();
            strip.clear();
            strip.show();
            a_delay = 1000/freq;
        }

        int i = 0;
        int d = 0;

        void iteration() {

            strip.clear();

            switch (animation){
                case loading:
                    strip.setPixelColor(d, strip.Color(0, 255, 0));
                    if (i%2==0) d++;
                    if (d>=led_num) d = 0;
                    break;
            }

            strip.show();
            delay(a_delay);
            i++;
        }
};