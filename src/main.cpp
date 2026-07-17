// CyclUno — Cyclops dev unit on an Arduino Uno, deck edition.
//
// Hardware:
//   128x128 SPI TFT (common ST7735 1.44 in): D11=MOSI, D13=SCK, D10=CS, D9=DC.
//   RES is externally pulled to 3.3 V via 10 kOhm; use level shifting unless
//   the TFT breakout explicitly marks its inputs 5 V-safe.
//   HW-504 joystick 1 (nav):  VRy=A0, VRx=A1, SW=D4 (to GND, internal pullup)
//   HW-504 joystick 2 (app):  VRy=A2, VRx=A3, SW=D8

//   buttons: B/back=D5, MODE=D2, X=D3, Y=D12
//   LEDs: REC=D6, link=D7, APP-mode=A4 (external; D13 is the SPI clock)
//
// Two personalities (MODE button toggles, A4 LED shows APP):
//   AION mode — joy1 + A/B drive the local HUD; joy2, X/Y are
//     forwarded to the host as MSG_INPUT_EVENT frames (aion turns them into
//     cockpit navigation: joy2=workspaces).
//   APP mode — local HUD input is suspended ("APP PAD" banner); joy2 raw
//     axes stream to the host, every face button forwards press+release, the
//     aion exposes it all as a uinput gamepad
//     ("CyclUno Pad") that drives whatever program aion spawned.
//
// Link: USB serial @115200 speaking the shared v2 framing — the same frames
// the XIAO speaks over BLE, so the whole brain pipeline is reused unchanged.
// Event payloads are pinned byte-for-byte to aion/src/aion/deck/protocol.py
// (host gate: test/test_deck.cpp).
//
// RAM: UnoHud 160 B, FrameDecoder 262 B, 4x JoyAxis + 2x RawAxisStream
// < 100 B — comfortably inside the ATmega328P's 2 KB.
#include <Arduino.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7735.h>
#include "cyclops_shared.h"
#include "cycluno.h"
#include "joynav.h"
#include "deck.h"

// ---- display: 128x128 SPI TFT -----------------------------------------
// Target: common 1.44 in ST7735 128x128 module. RES is held high externally
// (3.3 V through 10 kOhm); it deliberately does not consume an Uno pin.
// Hardware SPI on Uno: D11=MOSI, D13=SCK.
#define PIN_TFT_CS 10
#define PIN_TFT_DC 9
static Adafruit_ST7735 tft(PIN_TFT_CS, PIN_TFT_DC, -1);

#define PIN_JOY1_Y A0
#define PIN_JOY1_X A1
#define PIN_JOY2_Y A2
#define PIN_JOY2_X A3
#define PIN_BTN_A 4
#define PIN_BTN_B 5
#define PIN_LED_REC 6
#define PIN_LED_LINK 7
#define PIN_BTN_J2 8

// D9/D10/D11/D13 are TFT SPI/control. Face controls move accordingly.
#define PIN_BTN_MODE 2
#define PIN_BTN_X 3
#define PIN_BTN_Y 12
// D13 is SPI clock, so it cannot be used as a mode LED.
#define PIN_LED_MODE A4

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
    char tmp[64];  // HUD rows hold 16 chars; clamp the JSON payload hard
    if (n >= sizeof(tmp)) n = sizeof(tmp) - 1;
    memcpy(tmp, p, n); tmp[n] = 0;
    if (type == cyclops::MSG_DISPLAY_CMD || type == cyclops::MSG_NOTE) {
        hud.apply_display_cmd(tmp);
    }
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
// GFX built-in font is 6x8. The 16-column x 16-row HUD occupies 96x128 px.
struct TftSink : cycluno::RowSink {
    void row(uint8_t idx, const char* text) override {
        char line[cycluno::COLS + 1];
        uint8_t i = 0;
        while (text[i] && i < cycluno::COLS) { line[i] = text[i]; ++i; }
        while (i < cycluno::COLS) line[i++] = ' ';
        line[cycluno::COLS] = 0;
        tft.fillRect(0, idx * 8, cycluno::COLS * 6, 8, ST77XX_BLACK);
        tft.setCursor(0, idx * 8);
        tft.print(line);
    }
};
static TftSink sink;

static void rec_led(bool on) { digitalWrite(PIN_LED_REC, on ? HIGH : LOW); }

void setup() {
    Serial.begin(115200);
    tft.initR(INITR_144GREENTAB);
    tft.setRotation(0);
    tft.fillScreen(ST77XX_BLACK);
    tft.setTextWrap(false);
    tft.setTextSize(1);
    tft.setTextColor(ST77XX_WHITE, ST77XX_BLACK);

    pinMode(PIN_BTN_A, INPUT_PULLUP);
    pinMode(PIN_BTN_B, INPUT_PULLUP);
    pinMode(PIN_BTN_J2, INPUT_PULLUP);
    pinMode(PIN_BTN_MODE, INPUT_PULLUP);
    pinMode(PIN_BTN_X, INPUT_PULLUP);
    pinMode(PIN_BTN_Y, INPUT_PULLUP);
    pinMode(PIN_LED_REC, OUTPUT);
    pinMode(PIN_LED_LINK, OUTPUT);
    pinMode(PIN_LED_MODE, OUTPUT);


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
    static uint8_t stJ2 = 0, stX = 0, stY = 0, stM = 0;
    fwd_btn(edge(PIN_BTN_J2, stJ2), cycluno::DBTN_J2);
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
