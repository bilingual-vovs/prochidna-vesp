#include <Arduino.h>
#include <SPI.h>
#include <Adafruit_PN532.h>
#include "waveshare_pinout.h"
#include "db.h"
#include "led.h"

// Define the maximum number of consecutive connection failures before pausing
#define MAX_CONSECUTIVE_FAILURES 5 

class Nfc {
private:
    // PN532 object initialized with SPI pins
    Adafruit_PN532 nfc; 
    
    String last_uid_str = ""; 
    DataBase *db_ptr = nullptr; 

    Led led = Led(LED, LED_NUM); // Initialize LED object
    
    // Status flag to track if the PN532 chip is successfully initialized
    bool is_connected_ = false;
    uint8_t failure_count_ = 0;

    // Helper function to convert UID array to a hexadecimal String
    String uidArrayToString(uint8_t *uid, uint8_t uidLength) {
        String result = "";
        for (uint8_t i = 0; i < uidLength; i++) {
            if (uid[i] < 0x10) {
                result += "0"; 
            }
            result += String(uid[i], HEX); 
        }
        return result;
    }
    
    // Private method to handle the actual connection sequence
    bool reconnect() {
        Serial.println("Attempting PN532 reconnection...");
        
        // 1. Initiate SPI communication
        nfc.begin();
        
        // 2. Check PN532 firmware version
        uint32_t versiondata = nfc.getFirmwareVersion();

        if (versiondata) {
            // Success!
            nfc.SAMConfig();
            is_connected_ = true;
            failure_count_ = 0;
            Serial.println("PN532 Reconnection Successful!");
            return true;
        } else {
            // Failure
            failure_count_++;
            is_connected_ = false;
            Serial.printf("PN532 Reconnection Failed (Attempt %d)...\n", failure_count_);
            return false;
        }
    }


public:
    // Initialize the nfc object in the initializer list
    Nfc() : nfc(NFC_SCK, NFC_MISO, NFC_MOSI, NFC_CS) {} 

    // Public setup only runs once
    void setup(DataBase& dab) { 
        Serial.println("Starting NFC setup...");
        db_ptr = &dab; 
        led.setup();
        led.animation = waiting;

        // Attempt initial connection. If it fails, the loop will handle retries.
        if (!reconnect()) {
            Serial.println("Initial PN532 connection failed. Retrying in readTask.");
        }
    }

    void read() {
        // FIX: Check connection status before trying to read
        if (!nfc.getFirmwareVersion()) {
            // Don't flood the serial/CPU if it's failed too many times
            if (failure_count_ > MAX_CONSECUTIVE_FAILURES) {
                 vTaskDelay(pdMS_TO_TICKS(50)); // Pause retries for 500ms
            }
            // Try reconnecting
            reconnect(); 
            return; // Skip read cycle if connection failed this time
        }
        
        // --- If Connected (Original Read Logic) ---
        static uint8_t uid[7] = {0};
        uint8_t uidLength;
        
        // Attempt to read a Mifare card (50ms timeout is good)
        bool success = nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLength, 50);

        if (success) {
            String current_uid_str = uidArrayToString(uid, uidLength);
            
            if (current_uid_str != last_uid_str) {
                // New card found
                Serial.print("\nFound NEW NFC tag! UID (HEX): ");
                Serial.println(current_uid_str); 
                
                last_uid_str = current_uid_str;
                
                String data_to_log = "UID:" + current_uid_str + ", Time:" + String(millis());
                
                if (db_ptr) { 
                    db_ptr->appendRead(data_to_log);
                }
            }
        } else {
            // Card removed or read failed (resets the last UID)
            last_uid_str = "";
        }
    }

    // Task function
    void readTask(void * parameter) {
        for(;;) {
            read();
            vTaskDelay(pdMS_TO_TICKS(10)); // Added a slight yield for other tasks
        }
    }
};