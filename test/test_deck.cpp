// Deck host gate: event payload bytes (pinned to aion's protocol.py),
// APP-mode raw axis streaming, RAM budget.
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "deck.h"

using namespace cycluno;

static void test_pack() {
    uint8_t p[4];
    pack_input_event(SRC_JOY2, CODE_RAW_X, 300, p);
    assert(p[0] == 1 && p[1] == 2 && p[2] == 0x2C && p[3] == 0x01);
    pack_input_event(SRC_MODE, 0, MODE_APP, p);
    assert(p[0] == 4 && p[1] == 0 && p[2] == 1 && p[3] == 0);
    printf("PASS payload bytes match protocol.py\n");
}

static void test_raw_stream() {
    RawAxisStream s;
    s.calibrate(512);
    int16_t v;
    // resting at center: quiet
    assert(!s.update(512, 0, v));
    assert(!s.update(514, 100, v));                 // sub-threshold wiggle
    // deflect: sends centered value
    assert(s.update(700, 200, v) && v == 188);
    // immediately after: rate-limited even for big change
    assert(!s.update(900, 210, v));
    // after the interval: sends the new value
    assert(s.update(900, 200 + RawAxisStream::MIN_INTERVAL_MS, v) && v == 388);
    // small jitter below STEP: quiet
    assert(!s.update(903, 300, v));
    // return to rest: one final 0 so the host recenters
    assert(s.update(512, 400, v) && v == 0);
    // and then silence at rest
    assert(!s.update(513, 500, v));
    printf("PASS raw axis streaming\n");
}

static void test_ram() {
    printf("sizeof(RawAxisStream)=%zu\n", sizeof(RawAxisStream));
    assert(sizeof(RawAxisStream) <= 16);   // host: 8-byte long + padding; AVR is smaller
    printf("PASS RAM budget\n");
}

int main() {
    test_pack();
    test_raw_stream();
    test_ram();
    printf("OK: deck logic host gate passed\n");
    return 0;
}
