// Minimal blink-and-print test — no I2C, no IMU
#include <Arduino.h>
void setup() { Serial.begin(115200); pinMode(LED_BUILTIN, OUTPUT); }
void loop() {
    Serial.println("hello from cycluno");
    digitalWrite(LED_BUILTIN, !digitalRead(LED_BUILTIN));
    delay(500);
}
