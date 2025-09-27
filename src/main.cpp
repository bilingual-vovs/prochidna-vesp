#include <Arduino.h>
#include <db.h> // Include DataBase
#include <nfc.h> // Include Nfc
#include <led.h> // Include Led

DataBase db;
Nfc nfc;
Led led = Led(LED, LED_NUM); // Initialize LED object

void setup(){
    Serial.begin(115200);
    delay(1000);
    Serial.println("--- Starting Setup ---"); // Added print

    // 1. Initialize the File System
    Serial.println("Initializing DB..."); // Added print
    db.setup(); 
    Serial.println("DB Setup Complete (or failed and returned)."); // Added print
    
    led.setup();
    // 2. Initialize the NFC Reader
    Serial.println("Initializing NFC..."); // Added print
    nfc.setup(db, led); 
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

   xTaskCreate(
       [](void*){
           // Create a local Led object if it's not a static object
           // However, since led is a member of nfc, we reference it directly
           for(;;) {
               led.iteration();
               vTaskDelay(10 / portTICK_PERIOD_MS); // Small delay to yield to other tasks
           }
       },
       "LED Animation Task",
       2048, // Stack size
       NULL,
       1, // Priority
       NULL
   );
}

void loop(){
}