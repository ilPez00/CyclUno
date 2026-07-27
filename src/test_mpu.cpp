// MPU-6050 standalone test. Wire VCC→5V, GND→GND, SDA→A4, SCL→A5, AD0→GND.
#include <Arduino.h>
#include <Wire.h>

#define MPU_ADDR 0x68

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

void setup() {
    Serial.begin(115200);
    Wire.begin(); Wire.setClock(400000L);

    if (!i2c_probe(MPU_ADDR)) {
        Serial.println("MPU6050 NOT FOUND — check wiring (5V, GND, A4=SDA, A5=SCL, AD0→GND)");
        while (1) delay(1000);
    }

    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x6B); Wire.write(0x00); // wake
    Wire.write(0x6C); Wire.write(0x00); // all axes on
    Wire.write(0x19); Wire.write(0x07); // sample rate 125 Hz
    Wire.write(0x1B); Wire.write(0x08); // gyro ±500 dps
    Wire.write(0x1C); Wire.write(0x08); // accel ±4g
    Wire.endTransmission();

    delay(100);
    Serial.println("ax,ay,az,gx,gy,gz,pitch,roll");
}

void loop() {
    int16_t ax = reg_word(0x3B), ay = reg_word(0x3D), az = reg_word(0x3F);
    int16_t gx = reg_word(0x43), gy = reg_word(0x45), gz = reg_word(0x47);

    // pitch/roll from accel (degrees * 10 to drop decimal)
    int pitch = (int)(57.3 * atan2(ax, sqrt((double)ay*ay + (double)az*az)));
    int roll  = (int)(57.3 * atan2(ay, az));

    Serial.print(ax); Serial.print(',');
    Serial.print(ay); Serial.print(',');
    Serial.print(az); Serial.print(',');
    Serial.print(gx); Serial.print(',');
    Serial.print(gy); Serial.print(',');
    Serial.print(gz); Serial.print(',');
    Serial.print(pitch); Serial.print(',');
    Serial.println(roll);

    delay(100);
}
