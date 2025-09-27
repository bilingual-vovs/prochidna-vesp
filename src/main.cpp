#include <Arduino.h>
#include <db.h> // Include DataBase
#include <nfc.h> // Include Nfc

DataBase db;
Nfc nfc;

void setup(){
    Serial.begin(115200);
    delay(1000);
    Serial.println("--- Starting Setup ---"); // Added print

    // 1. Initialize the File System
    Serial.println("Initializing DB..."); // Added print
    db.setup(); 
    Serial.println("DB Setup Complete (or failed and returned)."); // Added print
    
    // 2. Initialize the NFC Reader
    Serial.println("Initializing NFC..."); // Added print
    nfc.setup(db); 
    Serial.println("NFC Setup Complete (or halted).");
    // 3. Create the NFC reading task
   xTaskCreate(
       [](void*){
           // Create a local Nfc object if it's not a static object
           // However, since nfc is a global object, we reference it directly
           for(;;) {
               nfc.read();
               vTaskDelay(10 / portTICK_PERIOD_MS); // Small delay to yield to other tasks
           }
       },
       "NFC Reader Task",
       4096, // Stack size
       NULL,
       1, // Priority
       NULL
   );
}

void loop(){
    // You can add your MQTT Uploader Task here or in loop()
    // For now, loop() is empty.
    vTaskDelay(pdMS_TO_TICKS(1000));
}