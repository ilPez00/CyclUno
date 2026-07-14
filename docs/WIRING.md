# CyclUno deck — assembly & wiring

![deck wiring](img/deck-wiring.svg)

![console layout](img/deck-layout.svg)

## Bill of materials

| Qty | Part | Role |
|-----|------|------|
| 1 | Arduino Uno R3 | brain-side of the cable, input polling |
| 1 | OLED SSD1306, I2C, 128x32 or 128x64 | aion status HUD |
| 2 | HW-504 joystick module | joy1 = nav (left hand), joy2 = app (right hand) |
| 1 | KY-040 rotary encoder module | the wheel: scroll + click |
| 4 | 6x6 mm push button | B (back), MODE, X, Y |
| 2 | LED + 220 Ω resistor | REC, LINK |
| — | breadboard + jumper wires | power rails, everything to GND |

Everything beyond joy1 + button B is **optional**: unwired pins read as
unpressed (internal pullups) and the unit degrades to the original
single-stick HUD.

## Pin map (single source of truth: `src/main.cpp`)

| Signal | Uno pin | Notes |
|--------|---------|-------|
| OLED SDA / SCL | A4 / A5 | I2C addr **0x3C** (some boards: 0x3D — change `OLED_ADDR`) |
| Joy1 VRy / VRx | A0 / A1 | nav stick |
| Joy1 SW (= button A) | D4 | active low, pullup |
| Joy2 VRy / VRx | A2 / A3 | app stick |
| Joy2 SW | D8 | stick click |
| KY-040 CLK / DT | **D2 / D3** | the Uno's only interrupt pins — the wheel owns them |
| KY-040 SW | D9 | wheel click |
| Button B | D5 | back / menu |
| Button MODE | D10 | AION ⇄ APP toggle |
| Button X / Y | D11 / D12 | pause / cancel (AION), pad west/north (APP) |
| REC LED | D6 | via 220 Ω to GND |
| LINK LED | D7 | via 220 Ω to GND |
| APP-mode LED | D13 | onboard — nothing to wire |

## Assembly order (each step leaves a working unit)

1. **Power rails.** Uno 5V → breadboard + rail, Uno GND → − rail.
2. **OLED.** VCC/GND → rails, SDA → A4, SCL → A5. Flash (`make flash`):
   the HUD boots to "CyclUno ready".
3. **Joy1.** VCC/GND → rails, VRy → A0, VRx → A1, SW → D4. Stick scrolls,
   press toggles REC.
4. **Button B** D5 → GND. Menu/back works.
5. **LEDs.** D6 → LED → 220 Ω → GND (REC), same for D7 (LINK).
6. **Wheel.** KY-040 + → 5 V rail, GND → − rail, CLK → D2, DT → D3,
   SW → D9. Detents arrive over serial as INPUT_EVENT frames.
7. **Joy2.** VCC/GND → rails, VRy → A2, VRx → A3, SW → D8.
8. **Buttons MODE/X/Y.** D10/D11/D12, each to GND. MODE toggles the D13 LED.

## Rules the wiring relies on

- **All buttons and both stick SWs close to GND** — firmware uses
  `INPUT_PULLUP`, no external resistors.
- **Sticks at rest during boot**: the first readings become the calibrated
  centers (joy nav *and* the APP-mode raw stream).
- **KY-040 must be on D2/D3.** The wheel is read by a falling-edge interrupt
  on CLK; on any other pins it will skip detents.
- The KY-040 module's onboard pullups want **+ wired to 5 V**, otherwise
  CLK/DT float.

## Smoke test

```bash
make test     # host gate: HUD + joynav + deck logic (no hardware needed)
make build    # AVR compile gate (RAM stays ~56%)
make flash
```

Then from the aion repo: `pip install -e ".[deck]"` and start `aion` — the
header shows `[DECK]`, the OLED starts mirroring aion status, the wheel
scrolls the cockpit. Press MODE (`[PAD]` in the header) and
`cat /proc/bus/input/devices | grep -A4 CyclUno` shows the gamepad.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| a stick direction is mirrored | set `JOY_FLIP_X` / `JOY_FLIP_Y` in `src/main.cpp` |
| wheel turns the wrong way | swap the CLK and DT jumpers |
| wheel double-steps per detent | some KY-040 clones detent on both edges — change the ISR to `CHANGE` and halve in software, or live with 2× |
| OLED dark | try addr 0x3D; check A4/A5 not swapped |
| ghost button presses | missing GND leg — every button must return to the − rail |
| APP mode does nothing on the host | `/dev/uinput` permission: `sudo usermod -aG input $USER`, re-login |
