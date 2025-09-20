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
        enum State animation = waiting;
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

        int approval_timer = 0;
        int denial_timer = 0;

        void approval(int time_ms){
            approval_timer = (int)floor(time_ms/a_delay);
            denial_timer = 0;
        }

        void denial(int time_ms){
            denial_timer = (int)floor(time_ms/a_delay);
            approval_timer = 0;
        }

        void iteration() {

            strip.clear();

            if (approval_timer > 0) {
                strip.fill(strip.Color(0, 255, 0), 0);
                approval_timer--;
            }
            else if (denial_timer > 0) {
                strip.fill(strip.Color(255, 0, 0), 0);
                denial_timer--;
            }
            else {
                switch (animation){
                    case loading:
                        strip.setPixelColor(d, strip.Color(0, 255, 0));
                        if (i%2==0) d++;
                        if (d>=led_num) d = 0;
                        break;
                    case waiting: 
                        strip.fill(strip.Color(0, 0, abs((int)(sin((float)i/20.0)*127.0 + 127.0))), 0);
                        break;
            }
            }

            strip.show();
            delay(a_delay);
            i++;
        }
};