# CyclUno

Cyclops dev unit on an Arduino Uno — HW-504 joystick edition. The wearable
product at breadboard scale: joystick + button + OLED + LEDs, wired to the
brain over USB serial. No WiFi/BT — the cable substitutes the radio while
exercising the exact same v2 frame protocol and the exact same brain pipeline
(transcriber → extractor → notes → HUD frames).

The brain side (SerialLink, `demo_cycluno.py`, bash TUI) lives in the
[cyclops](https://github.com/ilPez00/cyclops-wearable) repo; this repo is the
firmware only. Wire protocol: `include/cyclops_shared.h` (kept in sync with
cyclops `firmware/lib/cyclops_shared`).

## Why an Uno when the XIAO exists
- Input bring-up without risking the wearable board.
- The ATmega328P's 2 KB SRAM forces the lean-HUD discipline
  (`sizeof(UnoHud)` gated < 400 B by the host tests).
- Anything proven here (input handling, frame flow, pipeline) transfers
  upstream unchanged, because the wire protocol is shared.

## Wiring
| Part | Pin |
|------|-----|
| OLED SSD1306 (I2C, 0x3C) | SDA=A4, SCL=A5, VCC=5V, GND |
| HW-504 VRy / VRx | A0 / A1 (VCC=5V, GND) |
| HW-504 SW / button A | D4 (to GND, internal pullup) |
| Button B (menu/back) | D5 (to GND, internal pullup) |
| REC LED (+resistor) | D6 |
| Link LED (+resistor) | D7 |

Controls: **stick up/down** scrolls · **stick right / SW press** = A (REC
toggle on HOME, select in MENU) · **stick left / button B** = menu/back.
The stick alone drives the whole UI; the D5 button is a comfort duplicate.
Keep the stick at rest during boot — that reading becomes the calibrated
center. If a direction feels flipped for your module's mounting, set
`JOY_FLIP_Y` / `JOY_FLIP_X` in `src/main.cpp`.

D2/D3 (the Uno's only external-interrupt pins) are left free for future
peripherals; the joystick is polled.

## Build + flash
```
make test     # host gate: HUD logic + joystick nav, plain g++
make build    # pio run -e cycluno
make flash    # pio run -e cycluno -t upload
```

## Run the wired brain
From the cyclops repo:
```
python3 demo_cycluno.py       # auto-picks /dev/ttyACM*|ttyUSB*
```
Press **A** on the unit: the driver "transcribes" the next prerecorded take
through the real pipeline and streams the extracted notes back as NOTE frames
onto the OLED.
