#include <Arduino.h>
#include "led.h"
#include "buzzer.h"

const int buzzerPin = 4;

Melody* approvalMelody = new Melody(
    new int[4] {NOTE_C4, NOTE_E4, NOTE_G4, NOTE_C5},
    new int[4] {4, 4, 4, 4},
    new int[4] {128, 128, 128, 128},
    500,
    4
);

Melody* denialMelody = new Melody(
  new int[4] {NOTE_C5, NOTE_A4, NOTE_E4, NOTE_C4},
  new int[4] {4, 4, 4, 4},
  new int[4] {128, 128, 128, 128},
  500,
  4
);

Buzzer buzzer(buzzerPin, approvalMelody, denialMelody);

void setup() {
  buzzer.playApproval();
  delay(2000);
  buzzer.playDenial();
}

void loop() {
  // no need to repeat the melody.
}