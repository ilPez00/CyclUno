// CyclUno — Cyclops dev unit on an Arduino Uno, HW-504 joystick edition.
//
// Hardware:
//   OLED SSD1306 128x32 or 128x64, I2C (A4=SDA A5=SCL, addr 0x3C)
//   HW-504 joystick: VRy=A0, VRx=A1, SW=D4 (to GND, internal pullup)
//   button B on D5 (menu/back)
//   REC LED on D6, link LED on D7 (lit while frames arrive)
//
// Controls:
//   stick up/down   -> wheel (scroll notes / menu)
//   stick right     -> A (select / REC toggle)     — same as SW press
//   stick left      -> B (menu / back)             — same as button B
//   SW press        -> A
//   button B (D5)   -> B
// The stick alone drives the whole UI; the D5 button is a comfort duplicate.
// D2/D3 (the Uno's only external-interrupt pins) are left free.
//
// Link: USB serial @115200 speaking the shared v2 framing — the same frames
// the XIAO speaks over BLE, so the whole brain pipeline is reused unchanged.
// The brain side lives in the cyclops repo (device/serial_link.py,
// demo_cycluno.py feeding prerecorded fixtures).
//
// RAM: UnoHud is 160 B (host-gated < 400), FrameDecoder 262 B, two JoyAxis
// ~16 B, SSD1306Ascii is text-mode (no framebuffer) — comfortably inside the
// ATmega328P's 2 KB.
#include <Arduino.h>
#include <Wire.h>
#include "SSD1306Ascii.h"
#include "SSD1306AsciiWire.h"
#include "cyclops_shared.h"
#include "cycluno.h"
#include "joynav.h"

#define PIN_JOY_Y A0
#define PIN_JOY_X A1
#define PIN_BTN_A 4   // HW-504 SW
#define PIN_BTN_B 5
#define PIN_LED_REC 6
#define PIN_LED_LINK 7
#define OLED_ADDR 0x3C

// Set to 1 if stick-up scrolls the wrong way with your module's orientation.
#define JOY_FLIP_Y 0
#define JOY_FLIP_X 0

static SSD1306AsciiWire oled;
static cycluno::UnoHud hud;
static cycluno::JoyAxis joy_y, joy_x;

static void on_frame(uint8_t type, const uint8_t* p, size_t n, void* ctx);
static cyclops::FrameDecoder dec(on_frame, nullptr);

// ---- outgoing ---------------------------------------------------------
static void send_frame(uint8_t type, const uint8_t* payload, size_t n) {
    uint8_t buf[96];  // status/cmd frames only — audio never originates here
    size_t k = cyclops::encode_frame(type, payload, n, buf, sizeof(buf));
    if (k) Serial.write(buf, k);
}

static void send_cmd(uint8_t act) {
    char payload[32];
    int n = snprintf(payload, sizeof(payload), "{\"a\":%u,\"arg\":\"\"}", act);
    send_frame(cyclops::MSG_CMD, (const uint8_t*)payload, (size_t)n);
}

// ---- incoming ---------------------------------------------------------
static unsigned long last_rx_ms = 0;

static void on_frame(uint8_t type, const uint8_t* p, size_t n, void*) {
    last_rx_ms = millis();
    char tmp[64];  // notes are <= 21 chars on this display; clamp hard
    if (n >= sizeof(tmp)) n = sizeof(tmp) - 1;
    memcpy(tmp, p, n); tmp[n] = 0;
    if (type == cyclops::MSG_DISPLAY_CMD || type == cyclops::MSG_NOTE) {
        hud.apply_display_cmd(tmp);
    }
}

// ---- input ------------------------------------------------------------
// debounced active-low buttons
static bool pressed(uint8_t pin, uint8_t& state) {
    bool low = digitalRead(pin) == LOW;
    if (low && state == 0) { state = 1; return true; }
    if (!low) state = 0;
    return false;
}

static uint16_t joy_avg(uint8_t pin) {
    uint16_t acc = 0;
    for (uint8_t i = 0; i < 8; ++i) { acc += analogRead(pin); delay(2); }
    return acc / 8;
}

// ---- render sink -------------------------------------------------------
struct OledSink : cycluno::RowSink {
    void row(uint8_t idx, const char* text) override {
        oled.setCursor(0, idx);   // one text row per display row
        oled.print(text);
        oled.clearToEOL();
    }
};
static OledSink sink;

static void rec_led(bool on) { digitalWrite(PIN_LED_REC, on ? HIGH : LOW); }

void setup() {
    Serial.begin(115200);
    Wire.begin();
    Wire.setClock(400000L);
    oled.begin(&Adafruit128x32, OLED_ADDR);  // 128x64 works too: rows 0..3 used
    oled.setFont(System5x7);
    oled.clear();

    pinMode(PIN_BTN_A, INPUT_PULLUP);
    pinMode(PIN_BTN_B, INPUT_PULLUP);
    pinMode(PIN_LED_REC, OUTPUT);
    pinMode(PIN_LED_LINK, OUTPUT);

    // stick must be at rest during boot: its reading becomes the center
    joy_y.calibrate(joy_avg(PIN_JOY_Y));
    joy_x.calibrate(joy_avg(PIN_JOY_X));

    hud.send_cmd = send_cmd;
    hud.on_rec_led = rec_led;
    hud.init();
    hud.render(sink);
}

void loop() {
    // serial in -> decoder -> hud
    while (Serial.available()) dec.push((uint8_t)Serial.read());

    // inputs
    bool moved = false;
    unsigned long now = millis();
    int8_t dy = joy_y.update(analogRead(PIN_JOY_Y), now);
    if (dy) { hud.on_wheel(JOY_FLIP_Y ? -dy : dy); moved = true; }
    // X is edge-only: one action per flick, never auto-repeat (holding the
    // stick right must not machine-gun REC toggles).
    static int8_t x_prev = 0;
    joy_x.update(analogRead(PIN_JOY_X), now);
    int8_t xh = joy_x.held();
    if (JOY_FLIP_X) xh = -xh;
    if (xh != 0 && xh != x_prev) {
        if (xh > 0) hud.on_btn_a(); else hud.on_btn_b();  // right=select left=back
        moved = true;
    }
    x_prev = xh;
    static uint8_t stA = 0, stB = 0;
    if (pressed(PIN_BTN_A, stA)) { hud.on_btn_a(); moved = true; }
    if (pressed(PIN_BTN_B, stB)) { hud.on_btn_b(); moved = true; }

    // link LED: lit while frames arrived within the last 2 s
    digitalWrite(PIN_LED_LINK, (millis() - last_rx_ms < 2000) ? HIGH : LOW);

    // 1 Hz: toast decay + status frame out
    static unsigned long last_tick = 0;
    bool dirty = false;
    if (millis() - last_tick >= 1000) {
        last_tick = millis();
        dirty = hud.tick();
        char st[48];
        int n = hud.status_json(st, sizeof(st));
        send_frame(cyclops::MSG_STATUS, (const uint8_t*)st, (size_t)n);
    }

    // redraw on any input or decayed toast
    static unsigned long last_draw = 0;
    if ((dirty || moved || millis() - last_draw > 250)) {
        hud.render(sink);
        last_draw = millis();
    }
    delay(10);
}
