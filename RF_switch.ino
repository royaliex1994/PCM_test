#include <Arduino.h>

// define 4 GPIO pins for relaies controlling
const int relayPins[] = {13, 12, 14, 27};  // 

void setup() {
  Serial.begin(115200);  // initial Serials communication 
  // initialize pins to low state
  for (int i = 0; i < 4; i++) 
  {
    pinMode(relayPins[i], OUTPUT);
    digitalWrite(relayPins[i], LOW); 
  }
}

void loop() {
  // check if the serials port get data
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');  // read one line of the input string

    // controlling the relaies according to the command
    for (int i = 0; i < 4; i++) {
      if (command == String("ON") + String(i)) 
      {
        digitalWrite(relayPins[i], HIGH); 
        delay(100); // 100 ms pulse to switch relaies
        digitalWrite(relayPins[i], LOW);
      } 
      else if (command == String("OFF") + String(i)) 
      {
        digitalWrite(relayPins[i], LOW); 
      }
    }
  }
}

