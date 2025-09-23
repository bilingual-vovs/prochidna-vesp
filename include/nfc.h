#include <Arduino.h>
#include <SPI.h>
#include <Adafruit_PN532.h>

// Chip Select Pin (any GPIO)



class Nfc{

    int sck_pin;
    int miso_pin;
    int mosi_pin;
    int ss_pin;
    
    Adafruit_PN532 nfc;

    public:
        Nfc(int sck, int miso, int mosi, int ss): sck_pin(sck), miso_pin(miso), mosi_pin(mosi), ss_pin(ss), nfc(sck, miso, mosi, ss) {
        }

        void setup() {
            Serial.println("Initializing PN532...");

            // Begin PN532 communication
            nfc.begin();

            // Check PN532 firmware version
            uint32_t versiondata = nfc.getFirmwareVersion();
            if (!versiondata) {
                Serial.print("Didn't find PN53x board :(");
                while (1); // Halt
            }

            // Got chip, now configure it to read Mifare cards
            nfc.SAMConfig();

            Serial.println("PN532 initialized!");
            Serial.println("Waiting for NFC card...");
        }

        uint8_t* read(){
                    // Variables to store the card's UID and its length
            static uint8_t uid[] = {0, 0, 0, 0, 0, 0, 0};
            uint8_t uidLength;
            
            // Attempt to read a Mifare card
            // The timeout of 0 will not block the code, making the loop() run continuously
            bool success = nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLength, 50);

            if (success) {
                Serial.println("\nFound NFC tag!");
                
                Serial.print("UID Length: ");
                Serial.print(uidLength, DEC);
                Serial.println(" bytes");

                Serial.print("UID Value: ");
                for (uint8_t i = 0; i < uidLength; i++) {
                    if (uid[i] < 0x10) {
                        Serial.print("0"); // Add leading zero for single-digit hex values
                    }
                    Serial.print(uid[i], DEC);
                    Serial.print(" ");
                }
                Serial.println("");

               return uid;
            }
            return nullptr;
        }

        void readTask(void * parameter) {
            for(;;) {
                read();
            }
        }
};