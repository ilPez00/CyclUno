# CyclUno

Cyclops dev unit on an Arduino Uno — deck edition. Two jobs, one breadboard:

1. **Cyclops dev unit** — the wearable product at breadboard scale: joystick
   + buttons + OLED + LEDs, wired to the brain over USB serial. No WiFi/BT —
   the cable substitutes the radio while exercising the exact same v2 frame
   protocol and the exact same brain pipeline (transcriber → extractor →
   notes → HUD frames).
2. **aion control deck** — the physical console for the
   [aion](https://github.com/ilPez00/aion) cockpit TUI: two sticks, a
   two thumb joysticks, four face buttons, a mode switch. In AION mode the deck
   navigates the cockpit one-handed; in APP mode it becomes a Linux gamepad
   (uinput "CyclUno Pad") driving whatever program aion spawned. The OLED
   mirrors aion status. Jarvis, but with detents.

The cyclops brain side (SerialLink, `demo_cycluno.py`, bash TUI) lives in the
[cyclops](https://github.com/ilPez00/cyclops-wearable) repo; the aion deck
host side lives in aion (`src/aion/deck/`). This repo is the firmware only.
Wire protocol: `include/cyclops_shared.h` (kept in sync with cyclops
`firmware/lib/cyclops_shared`); input-event payloads: `include/deck.h`
(pinned byte-for-byte to aion's `deck/protocol.py` by `test/test_deck.cpp`).

## Why an Uno when the XIAO exists
- Input bring-up without risking the wearable board.
- The ATmega328P's 2 KB SRAM forces the lean-HUD discipline
  (`sizeof(UnoHud)` gated < 400 B by the host tests).
- Anything proven here (input handling, frame flow, pipeline) transfers
  upstream unchanged, because the wire protocol is shared.

## Wiring

![deck wiring](docs/img/deck-wiring.svg)

Full assembly guide — BOM, step-by-step order (each step leaves a working
unit), rules the wiring relies on, troubleshooting: **[docs/WIRING.md](docs/WIRING.md)**.

Quick pin map: OLED 128x128 (SSD1327 default / SH1107 via `-DDISPLAY_SH1107_128X128`)
A4/A5 · joy1 A0/A1+D4 · joy2 A2/A3+D8
B D5 · MODE D10 · X/Y D11/D12 · LEDs D6/D7 ·
APP LED D13 onboard. Everything beyond joy1 + B is optional: unwired pins
read as unpressed (internal pullups) and the unit degrades to the original
single-stick HUD.

![console layout](docs/img/deck-layout.svg)

### Controls — AION mode (D13 off)
Local HUD: **stick 1 up/down** scrolls · **stick 1 right / SW** = A (REC
toggle on HOME, select in MENU) · **stick 1 left / button B** = menu/back.
Forwarded to the aion cockpit: **joy2** = navigate workspaces · X/Y pause/cancel
**Y** = cancel · **stick 2 click** = activate.

### Controls — APP mode (MODE button, D13 on)
The deck is a gamepad: **stick 2** = analog axes · **A/B/X/Y + both stick
clicks + wheel click** = buttons · **joy2** = navigate. aion exposes it as a
uinput device named "CyclUno Pad"; spawn a program (`run app mpv …`) and play.

Keep both sticks at rest during boot — those readings become the calibrated
centers. If a direction feels flipped for your module's mounting, set
`JOY_FLIP_Y` / `JOY_FLIP_X` in `src/main.cpp`.

## Build + flash
```
make test     # host gate: HUD logic + joystick nav + deck logic, plain g++
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
