// JoyNav host gate: dead zone, immediate step, auto-repeat, re-arm,
// reversal, calibration offset, RAM budget.
#include <assert.h>
#include <stdio.h>
#include "joynav.h"

using cycluno::JoyAxis;

int main() {
    // RAM budget: two axes must stay negligible next to UnoHud's < 400 B.
    printf("sizeof(JoyAxis)=%zu\n", sizeof(JoyAxis));
    assert(sizeof(JoyAxis) <= 16);

    JoyAxis a;
    a.calibrate(512);

    // inside the dead zone: silence, wherever time is
    assert(a.update(512, 0) == 0);
    assert(a.update(512 + JoyAxis::DEADZONE, 100) == 0);      // boundary is quiet
    assert(a.update(512 - JoyAxis::DEADZONE, 200) == 0);
    printf("PASS dead zone quiet\n");

    // crossing the threshold: one immediate step, then quiet until repeat
    assert(a.update(900, 1000) == 1);
    assert(a.update(900, 1000 + JoyAxis::REPEAT_FIRST_MS - 1) == 0);
    printf("PASS immediate step, no early repeat\n");

    // hold: first repeat after REPEAT_FIRST_MS, then every REPEAT_MS
    assert(a.update(900, 1000 + JoyAxis::REPEAT_FIRST_MS) == 1);
    unsigned long t = 1000 + JoyAxis::REPEAT_FIRST_MS;
    assert(a.update(900, t + JoyAxis::REPEAT_MS - 1) == 0);
    assert(a.update(900, t + JoyAxis::REPEAT_MS) == 1);
    printf("PASS auto-repeat cadence\n");

    // back to center re-arms the immediate step
    assert(a.update(512, t + 300) == 0);
    assert(a.held() == 0);
    assert(a.update(100, t + 310) == -1);   // opposite side, instant
    printf("PASS re-arm after release\n");

    // direction reversal while deflected: new direction fires at once
    assert(a.update(950, t + 320) == 1);
    printf("PASS reversal immediate\n");

    // calibration offset respected (stick resting off-center)
    JoyAxis b;
    b.calibrate(600);
    assert(b.update(600, 0) == 0);
    assert(b.update(600 + JoyAxis::DEADZONE + 1, 10) == 1);
    assert(b.update(600, 20) == 0);
    assert(b.update(600 - JoyAxis::DEADZONE - 1, 30) == -1);
    printf("PASS calibration offset\n");

    printf("ALL JOYNAV TESTS PASSED\n");
    return 0;
}
