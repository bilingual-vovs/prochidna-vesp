#pragma once
#include <Arduino.h>
#include "pitches.h"

class Melody{
    public:
        int* notes;
        int* noteDurations;
        int* noteVolumes;
        int length;
        int duration;

        Melody(int* mel, int* dur, int* vol, int len, int dur1) : notes(mel), noteDurations(dur), noteVolumes(vol), length(len), duration(dur1) {}
};

class Buzzer{
    public:
        int buzzerPin;
        // notes in the melody:
        Melody* approval;
        Melody* denial;

        Buzzer(int pin, Melody* appr, Melody* den) : buzzerPin(pin), approval(appr), denial(den) {}

        void playMelody(Melody* melody) {
            // iterate over the notes of the melody:
            for (int thisNote = 0; thisNote < melody->duration; thisNote++) {
                // to calculate the note duration, take one second divided by the note type.
                //e.g. quarter note = 1000 / 4, eighth note = 1000/8, etc.
                int noteDuration = melody->length / melody->noteDurations[thisNote];
                tone(buzzerPin, melody->notes[thisNote], noteDuration);
                // to distinguish the notes, set a minimum time between them.
                // the note's duration + 30% seems to work well:
                int pauseBetweenNotes = noteDuration * 1.30;
                delay(pauseBetweenNotes);
                // stop the tone playing:
                noTone(buzzerPin);
            }
        }
        void playApproval(){
            playMelody(approval);
        }
        void playDenial(){
            playMelody(denial);
        }
        void off(){
            noTone(buzzerPin);
        }
};