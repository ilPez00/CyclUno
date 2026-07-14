// CyclUno — Cyclops dev unit on an Arduino Uno, deck edition.
//
// Hardware:
//   OLED 128x128, I2C (A4=SDA A5=SCL, addr 0x3C) — SSD1327 (default) or
//   SH1107; legacy SSD1306 128x64 panel via the DISPLAY_* define
//   HW-504 joystick 1 (nav):  VRy=A0, VRx=A1, SW=D4 (to GND, internal pullup)
//   HW-504 joystick 2 (app):  VRy=A2, VRx=A3, SW=D8
//   KY-040 rotary encoder:    CLK=D2, DT=D3 (the interrupt pins), SW=D9
//   buttons: B/back=D5, MODE=D10, X=D11, Y=D12
//   LEDs: REC=D6, link=D7, APP-mode=D13 (onboard)
//
// Two personalities (MODE button toggles, D13 LED shows APP):
//   AION mode — joy1 + A/B drive the local HUD; wheel, joy2, X/Y are
//     forwarded to the host as MSG_INPUT_EVENT frames (aion turns them into
//     cockpit navigation: wheel=scroll, wheel-click=run, joy2=workspaces).
//   APP mode — local HUD input is suspended ("APP PAD" banner); joy2 raw
//     axes stream to the host, every face button forwards press+release, the
//     wheel keeps stepping. aion exposes it all as a uinput gamepad
//     ("CyclUno Pad") that drives whatever program aion spawned.
//
// Link: USB serial @115200 speaking the shared v2 framing — the same frames
// the XIAO speaks over BLE, so the whole brain pipeline is reused unchanged.
// Event payloads are pinned byte-for-byte to aion/src/aion/deck/protocol.py
// (host gate: test/test_deck.cpp).
//
// RAM: UnoHud 160 B, FrameDecoder 262 B, 4x JoyAxis + 2x RawAxisStream +
// QuadDecoder < 60 B — comfortably inside the ATmega328P's 2 KB.
#include <Arduino.h>
#include <U8x8lib.h>
#include "cyclops_shared.h"
#include "cycluno.h"
#include "joynav.h"
#include "deck.h"

// ---- display selection --------------------------------------------------
// 128x128 I2C OLEDs come with two controllers; pick yours (or override with
// a -D build flag). Legacy 128x64 SSD1306 panels still work: the HUD
// simply clips to the top 8 rows.
#if defined(DISPLAY_SH1107_128X128)
static U8X8_SH1107_128X128_HW_I2C u8x8(U8X8_PIN_NONE);
#elif defined(DISPLAY_SSD1306_128X64)
static U8X8_SSD1306_128X64_NONAME_HW_I2C u8x8(U8X8_PIN_NONE);
#else  // default: Waveshare-style SSD1327 128x128
static U8X8_SSD1327_WS_128X128_HW_I2C u8x8(U8X8_PIN_NONE);
#endif

#define PIN_JOY1_Y A0
#define PIN_JOY1_X A1
#define PIN_JOY2_Y A2
#define PIN_JOY2_X A3
#define PIN_ENC_CLK 2
#define PIN_ENC_DT 3
#define PIN_BTN_A 4   // HW-504 #1 SW
#define PIN_BTN_B 5
#define PIN_LED_REC 6
#define PIN_LED_LINK 7
#define PIN_BTN_J2 8  // HW-504 #2 SW
#define PIN_BTN_WHEEL 9
#define PIN_BTN_MODE 10
#define PIN_BTN_X 11
#define PIN_BTN_Y 12
#define PIN_LED_MODE 13
#define OLED_ADDR 0x3C

// Set to 1 if a stick direction feels flipped for your module's mounting.
#define JOY_FLIP_Y 0
#define JOY_FLIP_X 0

static cycluno::UnoHud hud;
static cycluno::JoyAxis joy1_y, joy1_x, joy2_y, joy2_x;
static cycluno::RawAxisStream raw2_x, raw2_y;
static bool app_mode = false;

static void on_frame(uint8_t type, const uint8_t* p, size_t n, void* ctx);
static cyclops::FrameDecoder dec(on_frame, nullptr);

// ---- outgoing ---------------------------------------------------------
static void send_frame(uint8_t type, const uint8_t* payload, size_t n) {
    uint8_t buf[96];  // status/cmd/input frames only — audio never originates here
    size_t k = cyclops::encode_frame(type, payload, n, buf, sizeof(buf));
    if (k) Serial.write(buf, k);
}

static void send_cmd(uint8_t act) {
    char payload[32];
    int n = snprintf(payload, sizeof(payload), "{\"a\":%u,\"arg\":\"\"}", act);
    send_frame(cyclops::MSG_CMD, (const uint8_t*)payload, (size_t)n);
}

static void send_input(uint8_t src, uint8_t code, int16_t val) {
    uint8_t p[4];
    cycluno::pack_input_event(src, code, val, p);
    send_frame(cyclops::MSG_INPUT_EVENT, p, 4);
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

// ---- wheel (KY-040 on the interrupt pins) ------------------------------
// ISR applies the same rule QuadDecoder pins in the host gate: on CLK's
// falling edge, DT high = clockwise. Steps accumulate; loop() drains them.
static volatile int8_t wheel_acc = 0;

static void wheel_isr() {
    wheel_acc += digitalRead(PIN_ENC_DT) ? 1 : -1;
}

static int8_t take_wheel() {
    noInterrupts();
    int8_t w = wheel_acc;
    wheel_acc = 0;
    interrupts();
    return w;
}

// ---- input ------------------------------------------------------------
// debounced active-low buttons: edge() returns +1 press, -1 release, 0 none
static int8_t edge(uint8_t pin, uint8_t& state) {
    bool low = digitalRead(pin) == LOW;
    if (low && state == 0) { state = 1; return 1; }
    if (!low && state == 1) { state = 0; return -1; }
    return 0;
}

static uint16_t joy_avg(uint8_t pin) {
    uint16_t acc = 0;
    for (uint8_t i = 0; i < 8; ++i) { acc += analogRead(pin); delay(2); }
    return acc / 8;
}

// forward a button's press+release in APP mode, press-only intent in AION
static void fwd_btn(int8_t e, uint8_t code) {
    if (e == 0) return;
    if (app_mode || e > 0) send_input(cycluno::SRC_BTN, code, e > 0 ? 1 : 0);
}

static void set_mode(bool app) {
    app_mode = app;
    digitalWrite(PIN_LED_MODE, app ? HIGH : LOW);
    send_input(cycluno::SRC_MODE, 0, app ? cycluno::MODE_APP : cycluno::MODE_AION);
    hud.toast(app ? "APP PAD" : "AION");
}

// ---- render sink -------------------------------------------------------
// u8x8 draws 8x8 tiles, no framebuffer (2 KB RAM discipline preserved).
// Rows are padded to full width so leftovers never linger.
struct OledSink : cycluno::RowSink {
    void row(uint8_t idx, const char* text) override {
        char line[cycluno::COLS + 1];
        uint8_t i = 0;
        while (text[i] && i < cycluno::COLS) { line[i] = text[i]; ++i; }
        while (i < cycluno::COLS) line[i++] = ' ';
        line[cycluno::COLS] = 0;
        u8x8.drawString(0, idx, line);
    }
};
static OledSink sink;

static void rec_led(bool on) { digitalWrite(PIN_LED_REC, on ? HIGH : LOW); }

void setup() {
    Serial.begin(115200);
    u8x8.setI2CAddress(OLED_ADDR << 1);  // u8x8 wants the 8-bit form
    u8x8.begin();
    u8x8.setBusClock(400000L);
    u8x8.setFont(u8x8_font_chroma48medium8_r);
    u8x8.clear();

    pinMode(PIN_BTN_A, INPUT_PULLUP);
    pinMode(PIN_BTN_B, INPUT_PULLUP);
    pinMode(PIN_BTN_J2, INPUT_PULLUP);
    pinMode(PIN_BTN_WHEEL, INPUT_PULLUP);
    pinMode(PIN_BTN_MODE, INPUT_PULLUP);
    pinMode(PIN_BTN_X, INPUT_PULLUP);
    pinMode(PIN_BTN_Y, INPUT_PULLUP);
    pinMode(PIN_ENC_CLK, INPUT_PULLUP);
    pinMode(PIN_ENC_DT, INPUT_PULLUP);
    pinMode(PIN_LED_REC, OUTPUT);
    pinMode(PIN_LED_LINK, OUTPUT);
    pinMode(PIN_LED_MODE, OUTPUT);

    attachInterrupt(digitalPinToInterrupt(PIN_ENC_CLK), wheel_isr, FALLING);

    // sticks must be at rest during boot: their reading becomes the center
    joy1_y.calibrate(joy_avg(PIN_JOY1_Y));
    joy1_x.calibrate(joy_avg(PIN_JOY1_X));
    joy2_y.calibrate(joy_avg(PIN_JOY2_Y));
    joy2_x.calibrate(joy_avg(PIN_JOY2_X));
    raw2_x.calibrate(joy_avg(PIN_JOY2_X));
    raw2_y.calibrate(joy_avg(PIN_JOY2_Y));

    hud.send_cmd = send_cmd;
    hud.on_rec_led = rec_led;
    hud.init();
    hud.render(sink);
}

void loop() {
    // serial in -> decoder -> hud
    while (Serial.available()) dec.push((uint8_t)Serial.read());

    bool moved = false;
    unsigned long now = millis();

    // ---- wheel: aion nav in AION mode, scroll in APP mode (host decides)
    int8_t w = take_wheel();
    if (w) send_input(cycluno::SRC_WHEEL, cycluno::CODE_WHEEL_STEP, w);

    // ---- joy1 + A/B: local HUD in AION mode, gamepad buttons in APP mode
    static uint8_t stA = 0, stB = 0;
    int8_t eA = edge(PIN_BTN_A, stA);
    int8_t eB = edge(PIN_BTN_B, stB);
    int8_t dy1 = joy1_y.update(analogRead(PIN_JOY1_Y), now);
    static int8_t x1_prev = 0;
    joy1_x.update(analogRead(PIN_JOY1_X), now);
    int8_t x1h = joy1_x.held();
    if (JOY_FLIP_X) x1h = -x1h;
    if (!app_mode) {
        if (dy1) { hud.on_wheel(JOY_FLIP_Y ? -dy1 : dy1); moved = true; }
        // X is edge-only: one action per flick, never auto-repeat (holding
        // the stick right must not machine-gun REC toggles).
        if (x1h != 0 && x1h != x1_prev) {
            if (x1h > 0) hud.on_btn_a(); else hud.on_btn_b();
            moved = true;
        }
        if (eA > 0) { hud.on_btn_a(); moved = true; }
        if (eB > 0) { hud.on_btn_b(); moved = true; }
    } else {
        fwd_btn(eA, cycluno::DBTN_A);
        fwd_btn(eB, cycluno::DBTN_B);
    }
    x1_prev = x1h;

    // ---- joy2: nav steps in AION mode, raw axis stream in APP mode
    if (!app_mode) {
        int8_t dy2 = joy2_y.update(analogRead(PIN_JOY2_Y), now);
        int8_t dx2 = joy2_x.update(analogRead(PIN_JOY2_X), now);
        if (JOY_FLIP_Y) dy2 = -dy2;
        if (JOY_FLIP_X) dx2 = -dx2;
        if (dy2) send_input(cycluno::SRC_JOY2, cycluno::CODE_STEP_Y, dy2);
        if (dx2) send_input(cycluno::SRC_JOY2, cycluno::CODE_STEP_X, dx2);
    } else {
        int16_t v;
        if (raw2_x.update(analogRead(PIN_JOY2_X), now, v))
            send_input(cycluno::SRC_JOY2, cycluno::CODE_RAW_X, JOY_FLIP_X ? -v : v);
        if (raw2_y.update(analogRead(PIN_JOY2_Y), now, v))
            send_input(cycluno::SRC_JOY2, cycluno::CODE_RAW_Y, JOY_FLIP_Y ? -v : v);
    }

    // ---- face buttons: J2 stick click, wheel click, X, Y
    static uint8_t stJ2 = 0, stW = 0, stX = 0, stY = 0, stM = 0;
    fwd_btn(edge(PIN_BTN_J2, stJ2), cycluno::DBTN_J2);
    fwd_btn(edge(PIN_BTN_WHEEL, stW), cycluno::DBTN_WHEEL);
    fwd_btn(edge(PIN_BTN_X, stX), cycluno::DBTN_X);
    fwd_btn(edge(PIN_BTN_Y, stY), cycluno::DBTN_Y);

    // ---- MODE button: toggle personalities (never forwarded as a button)
    if (edge(PIN_BTN_MODE, stM) > 0) { set_mode(!app_mode); moved = true; }

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
    delay(5);
}
