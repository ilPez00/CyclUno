// CyclUno — mouse controller: joystick=mouse, click=left, button=right.
// IMU gestures (nod/shake/tilt/wheel) — active only if MPU6050 present.
// Outputs serial event frames @115200.
//
// Protocol:
//   M <dx> <dy>   mouse move   L 1/0    left click
//   R 1/0          right click  W -1/1   wheel
//   G <n>          gesture macro (1-7)
//   I 1/0          IMU status at boot
#include <Arduino.h>
#include <Wire.h>

#define PIN_JOY_Y A0
#define PIN_JOY_X A1
#define PIN_JOY_SW 2
#define PIN_BTN 3
#define MPU_ADDR 0x68

// ---- I2C (optional — only used if MPU responds) --------------------------
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

// ---- button gesture detector ---------------------------------------------
struct GestDet {
    uint16_t long_ms = 500, dbl_ms = 250;
    bool was = false, pend = false, long_fired = false;
    unsigned long down_at = 0, last_tap = 0;
    int poll(bool pressed, unsigned long now) {
        int out = 0;
        if (pressed && !was) { down_at = now; long_fired = false; }
        if (pressed && was && !long_fired && now - down_at >= long_ms) {
            long_fired = true; pend = false; out = 3;
        }
        if (!pressed && was) {
            if (!long_fired) {
                if (pend && now - last_tap <= dbl_ms) { pend = false; out = 2; }
                else { pend = true; last_tap = now; }
            }
        }
        if (pend && !pressed && now - last_tap > dbl_ms) { pend = false; out = 1; }
        was = pressed;
        return out;
    }
};

// ---- IMU gesture detector (nod/shake from gyro peaks) --------------------
struct ImuGest {
    static constexpr int THRESH = 4000, MIN_CROSS = 3, WINDOW = 10;
    int buf[WINDOW] = {0}, pos = 0, cnt = 0;
    int push(int gx, int gy) {
        int mag = abs(gy) + abs(gx) / 2;
        buf[pos] = mag; pos = (pos + 1) % WINDOW;
        if (cnt < WINDOW) cnt++;
        if (cnt < 4) return 0;
        int sum = 0;
        for (int i = 0; i < cnt; i++) sum += buf[i];
        int mean = sum / cnt, crosses = 0, prev = 0;
        for (int i = 0; i < cnt; i++) {
            int d = (buf[i] - mean > THRESH) ? 1 : (buf[i] - mean < -THRESH) ? -1 : 0;
            if (d && prev && d != prev) crosses++;
            if (d) prev = d;
        }
        if (crosses >= MIN_CROSS) { cnt = 0; pos = 0; return abs(gx) > abs(gy) ? 2 : 1; }
        return 0;
    }
};

// ---- globals --------------------------------------------------------------
static GestDet left_gest, right_gest;
static ImuGest imu_gest;
static bool left_was = false, right_was = false;
static int prev_tilt = 0;
static bool imu_ok = false;
static int imu_ax, imu_ay, imu_az, imu_gx, imu_gy, imu_gz;
static int imu_pitch, imu_roll;

// ---- emit event -----------------------------------------------------------
static void ev(const char* type, int a, int b) {
    Serial.print(type); Serial.print(' ');
    Serial.print(a);
    if (b != 0x7FFF) { Serial.print(' '); Serial.print(b); }
    Serial.println();
}

// ---- helpers --------------------------------------------------------------
static int apply_dz(int v, int dz) { return (v > dz || v < -dz) ? v : 0; }

// ---- setup ----------------------------------------------------------------
void setup() {
    Serial.begin(115200);
    pinMode(PIN_JOY_SW, INPUT_PULLUP);
    pinMode(PIN_BTN, INPUT_PULLUP);

    Wire.begin(); Wire.setClock(400000L);
    imu_ok = i2c_probe(MPU_ADDR);
    if (imu_ok) {
        Wire.beginTransmission(MPU_ADDR);
        Wire.write(0x6B); Wire.write(0x00);
        Wire.write(0x6C); Wire.write(0x00);
        Wire.write(0x19); Wire.write(0x07);
        Wire.write(0x1B); Wire.write(0x08);
        Wire.write(0x1C); Wire.write(0x08);
        Wire.endTransmission();
        delay(100);
    }
    ev("I", imu_ok ? 1 : 0, 0);
}

// ---- loop ----------------------------------------------------------------
void loop() {
    unsigned long now = millis();
    static unsigned long last = 0;
    if (now - last < 15) return;
    last = now;

    // joystick → mouse move (velocity curve)
    int jy = analogRead(PIN_JOY_Y) - 512;
    int jx = analogRead(PIN_JOY_X) - 512;
    jy = apply_dz(jy, 20);
    jx = apply_dz(jx, 20);
    if (jy || jx) {
        auto curve = [](int v) -> int {
            if (!v) return 0;
            int s = v > 0 ? 1 : -1, a = abs(v);
            int r = s * (a / 32 + (a * a) / (512 * 4));
            if (r > 32) r = 32; if (r < -32) r = -32;
            return r;
        };
        int dy = curve(jy), dx = curve(jx);
        if (dy || dx) ev("M", dx, dy);
    }

    // joystick SW → left click
    int ldown = !digitalRead(PIN_JOY_SW);
    int lg = left_gest.poll(ldown, now);
    if (ldown != left_was) { ev("L", ldown ? 1 : 0, 0); left_was = ldown; }
    if (lg == 2) ev("G", 4, 0);
    if (lg == 3) ev("G", 5, 0);

    // button → right click
    int rdown = !digitalRead(PIN_BTN);
    int rg = right_gest.poll(rdown, now);
    if (rdown != right_was) { ev("R", rdown ? 1 : 0, 0); right_was = rdown; }
    if (rg == 2) ev("G", 6, 0);
    if (rg == 3) ev("G", 7, 0);

    // IMU — only if found at boot
    if (imu_ok) {
        imu_gx = reg_word(0x43); imu_gy = reg_word(0x45); imu_gz = reg_word(0x47);
        imu_ax = reg_word(0x3B); imu_ay = reg_word(0x3D); imu_az = reg_word(0x3F);
        imu_pitch = (int)(57.3 * atan2(imu_ax, sqrt((double)imu_ay*imu_ay + (double)imu_az*imu_az)));
        imu_roll  = (int)(57.3 * atan2(imu_ay, imu_az));

        int tilt = 0;
        if (imu_roll > 30) tilt = -1;
        else if (imu_roll < -30) tilt = 1;
        if (tilt && tilt != prev_tilt) ev("W", tilt, 0);
        prev_tilt = tilt;

        int ig = imu_gest.push(imu_gx, imu_gy);
        if (ig == 1) ev("G", 1, 0);
        if (ig == 2) ev("G", 2, 0);
    }
}
