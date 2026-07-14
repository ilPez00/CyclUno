// Deck host gate: event payload bytes (pinned to aion's protocol.py),
// KY-040 quadrature decoding, APP-mode raw axis streaming, RAM budget.
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "deck.h"

using namespace cycluno;

static void test_pack() {
    uint8_t p[4];
    pack_input_event(SRC_WHEEL, CODE_WHEEL_STEP, -3, p);
    // struct.pack("<BBh", 2, 0, -3) == 02 00 fd ff
    assert(p[0] == 2 && p[1] == 0 && p[2] == 0xFD && p[3] == 0xFF);
    pack_input_event(SRC_JOY2, CODE_RAW_X, 300, p);
    assert(p[0] == 1 && p[1] == 2 && p[2] == 0x2C && p[3] == 0x01);
    pack_input_event(SRC_MODE, 0, MODE_APP, p);
    assert(p[0] == 4 && p[1] == 0 && p[2] == 1 && p[3] == 0);
    printf("PASS payload bytes match protocol.py\n");
}

static void test_quad() {
    QuadDecoder q;
    // idle high, no motion
    assert(q.update(true, true) == 0);
    // CLK falls with DT high -> clockwise detent
    assert(q.update(false, true) == 1);
    // held low: nothing
    assert(q.update(false, true) == 0);
    // CLK back high: nothing (only falling edge counts)
    assert(q.update(true, true) == 0);
    // CLK falls with DT low -> counter-clockwise
    assert(q.update(false, false) == -1);
    assert(q.update(true, false) == 0);
    // bounce on the high level: quiet
    assert(q.update(true, true) == 0);
    assert(q.update(true, false) == 0);
    printf("PASS quadrature decode\n");
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
    printf("sizeof(QuadDecoder)=%zu sizeof(RawAxisStream)=%zu\n",
           sizeof(QuadDecoder), sizeof(RawAxisStream));
    assert(sizeof(QuadDecoder) <= 4);
    assert(sizeof(RawAxisStream) <= 16);   // host: 8-byte long + padding; AVR is smaller
    printf("PASS RAM budget\n");
}

int main() {
    test_pack();
    test_quad();
    test_raw_stream();
    test_ram();
    printf("OK: deck logic host gate passed\n");
    return 0;
}
