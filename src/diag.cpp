// CyclUno wiring diag — joystick + button + MPU6050. Serial @115200.
// I2C with timeout-safe probe: scans first, skips if nothing found.
#include <Arduino.h>
#include <Wire.h>

#define PIN_JOY_Y A0
#define PIN_JOY_X A1
#define PIN_JOY_SW 2
#define PIN_BTN 3
#define MPU_ADDR 0x68

// I2C probe: returns true if device ACKs at addr
static bool i2c_probe(uint8_t addr) {
    Wire.beginTransmission(addr);
    return Wire.endTransmission() == 0;
}

static int16_t reg_word(uint8_t reg) {
    Wire.beginTransmission(MPU_ADDR); Wire.write(reg);
    if (Wire.endTransmission() != 0) return 0;
    Wire.requestFrom((int)MPU_ADDR, 2);
    if (Wire.available() < 2) return 0;
    uint8_t h = Wire.read(), l = Wire.read();
    return (int16_t)((h << 8) | l);
}

static bool mpu_found = false;

void setup() {
    Serial.begin(115200);
    pinMode(PIN_JOY_SW, INPUT_PULLUP);
    pinMode(PIN_BTN, INPUT_PULLUP);
    Wire.begin(); Wire.setClock(400000L);

    // I2C scan — find every device on the bus
    Serial.print("I2C scan:");
    for (uint8_t a = 1; a < 120; a++) {
        if (i2c_probe(a)) {
            Serial.print(" 0x"); if (a < 16) Serial.print("0");
            Serial.print(a, HEX);
        }
    }
    Serial.println();

    mpu_found = i2c_probe(MPU_ADDR);
    if (mpu_found) {
        // wake + configure
        Wire.beginTransmission(MPU_ADDR);
        Wire.write(0x6B); Wire.write(0x00);
        Wire.endTransmission();
        Wire.beginTransmission(MPU_ADDR);
        Wire.write(0x6C); Wire.write(0x00);
        Wire.endTransmission();
        delay(100);
        Serial.println("MPU6050 OK");
    }
    Serial.println("JOY_Y,JOY_X,SW|BTN|ax,ay,az|gx,gy,gz|pitch,roll");
}

void loop() {
    int jy = analogRead(PIN_JOY_Y), jx = analogRead(PIN_JOY_X);
    int jsw = !digitalRead(PIN_JOY_SW), btn = !digitalRead(PIN_BTN);

    Serial.print(jy); Serial.print(',');
    Serial.print(jx); Serial.print(',');
    Serial.print(jsw); Serial.print('|');
    Serial.print(btn);

    if (mpu_found) {
        int16_t ax = reg_word(0x3B), ay = reg_word(0x3D), az = reg_word(0x3F);
        int16_t gx = reg_word(0x43), gy = reg_word(0x45), gz = reg_word(0x47);
        int pitch = (int)(57.3 * atan2(ax, sqrt((double)ay*ay + (double)az*az)));
        int roll  = (int)(57.3 * atan2(ay, az));
        Serial.print('|');
        Serial.print(ax); Serial.print(','); Serial.print(ay); Serial.print(','); Serial.print(az);
        Serial.print('|');
        Serial.print(gx); Serial.print(','); Serial.print(gy); Serial.print(','); Serial.print(gz);
        Serial.print('|');
        Serial.print(pitch); Serial.print(','); Serial.print(roll);
    }
    Serial.println();
    delay(100);
}
