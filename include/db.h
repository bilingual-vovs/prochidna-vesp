#include <Arduino.h>
#include <LittleFS.h>
#include <FS.h>

#define FORMAT_ON_STARTUP true

#define FORMAT_LITTLEFS_IF_FAILED true

#define PATH "/outbox.txt"

class DataBase{
    public:

        FS fs = LittleFS;

        DataBase(){
            if(!LittleFS.begin(FORMAT_ON_STARTUP)){
                Serial.println("LittleFS Mount Failed");
                return;
            }
        }

        String readFile(const char * path){
            Serial.printf("Reading file: %s\r\n", path);

            File file = fs.open(path);
            if(!file || file.isDirectory()){
                Serial.println("- failed to open file for reading");
                return "";
            }

            String content = "";
            while(file.available()){
                content += (char)file.read();
            }
            file.close();

            return content;
        }

        String readFirstLine(const char * path){
            File file = fs.open(path);
            if(!file || file.isDirectory()){
                Serial.println("- failed to open file for reading");
                return "";
            }
            String content = file.readStringUntil('\n');
            file.close();
            return content;
        }

        void writeFile(const char * path, const char * message){
            Serial.printf("Writing file: %s\r\n", path);

            File file = fs.open(path, FILE_WRITE);
            if(!file){
                Serial.println("- failed to open file for writing");
                return;
            }
            if(file.print(message)){
                Serial.println("- file written");
            } else {
                Serial.println("- write failed");
            }
            file.close();
        }

        int appendFile(const char * path, const char * message){
            Serial.printf("Appending to file: %s\r\n", path);

            File file = fs.open(path, FILE_APPEND);
            if(!file){
                Serial.println("- failed to open file for appending");
                return 1;
            }
            if(file.print(message)){
                Serial.println("- message appended");
                return 0;
            } else {
                Serial.println("- append failed");
                return 2;
            }
            file.close();
        }

        void deleteFile(const char * path){
            Serial.printf("Deleting file: %s\r\n", path);
            if(fs.remove(path)){
                Serial.println("- file deleted");
            } else {
                Serial.println("- delete failed");
            }
        }

        int appendRead(String data) {
            // Ensure data ends with a newline character for proper logging/parsing
            if (!data.endsWith("\n")) {
                data += "\n";
            }
            if (!fs.exists(PATH)) {
                writeFile(PATH, data.c_str());
                return 0; // Successfully created and wrote to the file
            }
            return appendFile(PATH, data.c_str());
        }

        String getRead(){
            return readFirstLine(PATH);
        }

        int removeRead(String read){
            //delete first line from file if it matches read
            String firstLine = readFirstLine(PATH);
            if(firstLine != read){
                Serial.println("- read does not match");
                return 1;
            }
            File file = fs.open(PATH);
            if(!file || file.isDirectory()){
                Serial.println("- failed to open file for reading");
                return 2;
            }
            String content = "";
            while(file.available()){
                content += (char)file.read();
            }
            file.close();
            int firstLineEnd = content.indexOf('\n');
            if(firstLineEnd == -1){
                //only one line in file
                deleteFile(PATH);
                return 0;
            }
            content = content.substring(firstLineEnd + 1);
            writeFile(PATH, content.c_str());
            return 0;
        }
};

