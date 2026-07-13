// JoyNav — HW-504 analog joystick to discrete nav steps.
//
// Pure logic, no Arduino dependencies: callers feed raw ADC readings
// (0..1023) plus a millisecond clock, and get back -1 / 0 / +1 step events.
// This keeps the dead-zone / auto-repeat behaviour host-testable
// (test_joynav.cpp) exactly like UnoHud.
//
// Behaviour per axis:
//   - dead zone around the calibrated center: no events
//   - crossing the threshold emits one step immediately (feels like a click)
//   - holding the deflection auto-repeats: first after REPEAT_FIRST_MS,
//     then every REPEAT_MS (list scrolling without detents)
//   - returning inside the dead zone re-arms the immediate step
//   - reversing direction while deflected emits the new direction at once
//
// sizeof(JoyAxis) is gated small in test_joynav.cpp — RAM discipline as in
// cycluno.h (ATmega328P: 2 KB total).
#pragma once
#include <stdint.h>

namespace cycluno {

class JoyAxis {
public:
    // Tunables (raw ADC units of a 0..1023 range, and milliseconds).
    static const int16_t DEADZONE = 160;         // of the ~512 half-swing
    static const uint16_t REPEAT_FIRST_MS = 350; // hold delay before repeat
    static const uint16_t REPEAT_MS = 140;       // repeat rate afterwards

    // Set the resting-position reading (sample the axis at boot).
    void calibrate(uint16_t raw_center) { center_ = (int16_t)raw_center; }

    // Feed one reading; returns a step event: -1, 0 or +1.
    int8_t update(uint16_t raw, unsigned long now_ms) {
        int16_t d = (int16_t)raw - center_;
        int8_t dir = 0;
        if (d > DEADZONE) dir = 1;
        else if (d < -DEADZONE) dir = -1;

        if (dir == 0) { held_ = 0; return 0; }
        if (dir != held_) {                    // fresh press or reversal
            held_ = dir;
            next_ms_ = now_ms + REPEAT_FIRST_MS;
            return dir;
        }
        if ((long)(now_ms - next_ms_) >= 0) {  // wrap-safe comparison
            next_ms_ = now_ms + REPEAT_MS;
            return dir;
        }
        return 0;
    }

    int8_t held() const { return held_; }

private:
    int16_t center_ = 512;
    int8_t held_ = 0;
    unsigned long next_ms_ = 0;
};

}  // namespace cycluno
