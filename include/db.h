#pragma once
#include <Arduino.h>
#include <LittleFS.h>
#include <FS.h>

#define FORMAT_ON_STARTUP true
#define PATH "/outbox.txt" // Use absolute path starting with '/'

class DataBase {
public:
    // FIX: Use a reference '&' and initialize it in the constructor list
    FS &fs; 

    // FIX: Initialize the reference 'fs' with the global LittleFS object
    DataBase() : fs(LittleFS) { 
        // NOTE: Initialization of the file system is now moved to setup() 
        // because it relies on the Arduino environment being ready.
    }

    // FIX: Moved LittleFS initialization into its own setup function
    void setup() {
        if (!LittleFS.begin(FORMAT_ON_STARTUP)) {
            Serial.println("LittleFS Mount Failed");
            // In a constructor/setup, it's better to halt or set an error flag
            return; 
        }
        // Ensure the file exists if we're going to read it later (prevents initial errors)
        if (!fs.exists(PATH)) {
            writeFile(PATH, ""); // Create an empty file if it doesn't exist
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

    String readFirstLine(const char * path){
        File file = fs.open(path);
        if(!file || file.isDirectory()){
            // FIX: Check for file existence to distinguish from other errors
            if (!fs.exists(path)) {
                Serial.println("- failed to open file for reading: File does not exist.");
            } else {
                Serial.println("- failed to open file for reading: Unknown error.");
            }
            return "";
        }
        String content = file.readStringUntil('\n');
        file.close();
        // Remove trailing carriage return if present, as it interferes with matching
        if (content.endsWith("\r")) content.remove(content.length() - 1);
        return content;
    }
    
    // FIX: Logic for appending. Simplified file existence check is now in the logic itself.
    int appendRead(String data) {
        if (!data.endsWith("\n")) {
            data += "\n";
        }
        // Check if file exists, if not, write (create) it, otherwise append.
        if (!fs.exists(PATH)) {
            // Use writeFile which opens with FILE_WRITE, creating the file
            writeFile(PATH, data.c_str());
            return 0; 
        }
        return appendFile(PATH, data.c_str()); // Use appendFile if it already exists
    }

    String getRead() {
        return readFirstLine(PATH);
    }

    int removeRead(String read) {
        // FIX: The core logic for removing the first line is complex and risky. 
        // This is a direct implementation of the requested logic:
        
        String firstLine = readFirstLine(PATH);
        if (firstLine.length() == 0) {
            return 0; // File is empty, nothing to remove
        }
        
        // Ensure the string 'read' (which came from getRead) matches the line in the file
        if (firstLine != read) {
            Serial.printf("- read does not match. Expected: [%s], Found: [%s]\n", read.c_str(), firstLine.c_str());
            return 1;
        }

        // 1. Read the rest of the file's content
        File file = fs.open(PATH);
        if(!file) return 2; // Should not happen if getRead worked

        // Skip the first line by seeking past its length
        int firstLineLength = firstLine.length();
        // +1 for the newline character which was consumed by readStringUntil('\n')
        file.seek(firstLineLength + 1, SeekSet); 
        
        String restOfContent = "";
        while(file.available()){
            restOfContent += (char)file.read();
        }
        file.close();

        // 2. Rewrite the file with the remaining content
        if (restOfContent.length() == 0) {
            deleteFile(PATH);
        } else {
            writeFile(PATH, restOfContent.c_str()); // Overwrite the file with the remaining content
        }
        
        return 0;
    }
};