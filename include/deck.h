// Deck — CyclUno as aion's physical console: second stick, extra buttons,
// and a mode switch.
//
// Two modes, toggled by the MODE button (D2):
//   AION: joy1 + A/B drive the local HUD as before; joy2, X/Y and the face
//         buttons are forwarded to the host as MSG_INPUT_EVENT frames — aion
//         turns them into navigation Intents.
//   APP:  local HUD input is suspended; joy2 raw axes stream to the host
//         (which exposes them as a Linux uinput gamepad, "CyclUno Pad"), and
//         every face button (A/B/X/Y/J2) forwards press AND release.
//
// INPUT_EVENT payload (4 bytes, little-endian int16 value), kept in lockstep
// with aion/src/aion/deck/protocol.py:
//   src:  0 JOY1 · 1 JOY2 · 2 (was WHEEL) · 3 BTN · 4 MODE
//   joy codes:   0 step-x ±1 · 1 step-y ±1 · 2 raw-x · 3 raw-y (centered)
//   btn codes:   0 A · 1 B · 2 J2-SW · 3 (was WHEEL-SW) · 4 MODE · 5 X · 6 Y
//                (val 1=down 0=up)
//   mode codes:  0 (val 0=AION 1=APP), sent on every toggle
//
// Everything here is pure logic (no Arduino headers) so it is host-testable:
// test_deck.cpp feeds pin levels / readings and asserts emitted events.
// RAM gates: sizeof(RawAxisStream) tiny.
#pragma once
#include <stdint.h>

namespace cycluno {

// ---- event enums (mirror protocol.py) ------------------------------------
// NOTE: the wheel (src 2, btn 3) was removed; its numeric codes are left
// unused on purpose so existing aion pairing stays byte-compatible.
static const uint8_t SRC_JOY1 = 0, SRC_JOY2 = 1, SRC_WHEEL = 2,
                     SRC_BTN = 3, SRC_MODE = 4;
static const uint8_t CODE_STEP_X = 0, CODE_STEP_Y = 1,
                     CODE_RAW_X = 2, CODE_RAW_Y = 3;
static const uint8_t DBTN_A = 0, DBTN_B = 1, DBTN_J2 = 2, DBTN_WHEEL = 3,
                     DBTN_MODE = 4, DBTN_X = 5, DBTN_Y = 6;
static const uint8_t MODE_AION = 0, MODE_APP = 1;

// Pack one input event into a 4-byte payload. Buffer must hold 4 bytes.
inline void pack_input_event(uint8_t src, uint8_t code, int16_t val,
                             uint8_t* out) {
    out[0] = src;
    out[1] = code;
    out[2] = (uint8_t)(val & 0xFF);
    out[3] = (uint8_t)((val >> 8) & 0xFF);
}

// ---- debounced button -------------------------------------------------------
// The old edge() helper claimed "debounced" but only tracked level flips: any
// contact bounce spanning two loop iterations double-fired (machine-gun REC
// toggles). Real debounce: a level change is accepted only once the raw input
// has been stable for SETTLE_MS. Sub-settle glitches emit nothing.
class DebouncedButton {
public:
    static const uint16_t SETTLE_MS = 20;

    // Feed the raw level (true = pressed) + clock.
    // Returns +1 on a settled press, -1 on a settled release, 0 otherwise.
    int8_t update(bool pressed, unsigned long now_ms) {
        if (pressed != raw_) { raw_ = pressed; settle_ms_ = now_ms; }
        if (raw_ != state_ &&
            (long)(now_ms - settle_ms_) >= (long)SETTLE_MS) {  // wrap-safe
            state_ = raw_;
            return state_ ? 1 : -1;
        }
        return 0;
    }

    bool pressed() const { return state_; }

private:
    bool raw_ = false;
    bool state_ = false;
    unsigned long settle_ms_ = 0;
};

// ---- APP-mode raw axis streaming -------------------------------------------
// Decides when a raw axis reading is worth a frame: on meaningful change
// (> STEP counts) or on returning to center, rate-limited to MIN_INTERVAL_MS.
// Keeps serial traffic low so the Uno's loop never starves.
class RawAxisStream {
public:
    static const int16_t STEP = 8;              // ADC counts of change to send
    static const uint16_t MIN_INTERVAL_MS = 30; // max ~33 frames/s per axis

    void calibrate(uint16_t raw_center) { center_ = (int16_t)raw_center; }

    // Returns true when `out_val` should be sent (centered value).
    bool update(uint16_t raw, unsigned long now_ms, int16_t& out_val) {
        int16_t v = (int16_t)raw - center_;
        if ((long)(now_ms - next_ms_) < 0) return false;
        int16_t d = (int16_t)(v - last_sent_);
        if (d < 0) d = (int16_t)-d;
        bool centered_now = (v > -STEP && v < STEP);
        bool was_off = (last_sent_ <= -STEP || last_sent_ >= STEP);
        if (d >= STEP || (centered_now && was_off)) {
            last_sent_ = centered_now ? 0 : v;
            out_val = last_sent_;
            next_ms_ = now_ms + MIN_INTERVAL_MS;
            return true;
        }
        return false;
    }

private:
    int16_t center_ = 512;
    int16_t last_sent_ = 0;
    unsigned long next_ms_ = 0;
};

}  // namespace cycluno
