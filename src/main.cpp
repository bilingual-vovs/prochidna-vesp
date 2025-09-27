#include <Arduino.h>
#include <db.h>

//  You only need to format LittleFS the first time you run a
//  test or else use the LITTLEFS plugin to create a partition 
//  https://github.com/lorol/arduino-esp32littlefs-plugin
DataBase db = DataBase();

void setup(){
    Serial.begin(115200);

    delay(2000);
    for (int i = 0; i < 20; i++) {
        int r = db.removeRead(db.getRead());
        Serial.printf("Remove read result: %d\r\n", r);

    }

    Serial.println("Done");
    Serial.println(db.readFile(PATH));
    // Use the official core's LittleFS object, which should be globally available.
    
}

void loop(){

}