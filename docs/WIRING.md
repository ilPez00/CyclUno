# CyclUno deck — assembly & wiring

![deck wiring](img/deck-wiring.svg)

![console layout](img/deck-layout.svg)

## Bill of materials

| Qty | Part | Role |
|-----|------|------|
| 1 | Arduino Uno R3 | brain-side of the cable, input polling |
| 1 | OLED 128x128, I2C — SSD1327 (default) or SH1107 | aion status HUD, 16x16 text grid |
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
| OLED SDA / SCL | A4 / A5 | I2C addr **0x3C** (some boards: 0x3D — change `OLED_ADDR`); controller via `DISPLAY_*` define, see below |
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

## Per-pin fan-out (direct wiring, no breadboard)

Every signal pin carries exactly **one** wire; only 5 V and GND branch.
17 signal wires + the power tree, 21–27 wires total depending on chaining.

| Uno pin | wires out | destination |
|---------|-----------|-------------|
| D2 | 1 | KY-040 CLK |
| D3 | 1 | KY-040 DT |
| D4 | 1 | HW-504 #1 SW |
| D5 | 1 | button B |
| D6 | 1 | REC LED anode |
| D7 | 1 | LINK LED anode |
| D8 | 1 | HW-504 #2 SW |
| D9 | 1 | KY-040 SW |
| D10 | 1 | button MODE |
| D11 | 1 | button X |
| D12 | 1 | button Y |
| D13 | 0 | onboard LED — nothing to wire |
| A0 | 1 | HW-504 #1 VRy |
| A1 | 1 | HW-504 #1 VRx |
| A2 | 1 | HW-504 #2 VRy |
| A3 | 1 | HW-504 #2 VRx |
| A4 | 1 | OLED SDA |
| A5 | 1 | OLED SCL |
| **5V** | 1 socket, **4 loads** | OLED VCC · joy1 +5V · joy2 +5V · KY-040 + |
| **GND** | 3 sockets, **10 returns** | see split below |

**5 V**: the Uno header has a single 5V socket. Run one wire to a splice
(solder joint, Wago, or a chain) and branch 4 ways from there — or
daisy-chain module-to-module: `5V → joy1 → joy2 → KY-040 → OLED`.

**GND**: the Uno has 3 GND sockets (two on the power header, one on the
digital header next to D13). 10 things need a return; a sane split:

| GND socket | chain |
|------------|-------|
| power #1 | joy1 GND → joy2 GND → KY-040 GND → OLED GND (module chain) |
| power #2 | button B → MODE → X → Y (one wire hopping leg-to-leg) |
| digital (by D13) | REC resistor → LINK resistor |

**No extra GND for the clicks**: HW-504 SW and KY-040 SW switch against
their own module's GND pin internally — the module GND wire already
carries them. Only the 4 standalone push buttons need a GND leg.

### I2C notes (the OLED pair)

- Exactly **2 signal wires**: A4 → SDA, A5 → SCL (plus VCC/GND from the
  power chain). No resistors to add: these OLED modules carry their own
  pull-ups to VCC.
- On an Uno R3 the two sockets labeled **SDA/SCL next to AREF are the same
  net as A4/A5** — use whichever is handier, they are not extra pins. And
  since I2C owns them, A4/A5 are not available as analog inputs.
- The firmware runs the bus at **400 kHz** (`Wire.setClock(400000L)`):
  keep the SDA/SCL pair short (< ~25 cm) and routed together, away from
  the joystick analog lines. Longer run needed? Drop to 100 kHz
  (`Wire.setClock(100000L)` in `src/main.cpp`).
- I2C is a **bus**: future devices (e.g. the MCP23017 button expander from
  the upgrade notes) piggyback on the *same two wires* in parallel — new
  address, zero new Uno pins. Just don't duplicate address 0x3C.

## Assembly order (each step leaves a working unit)

1. **Power rails.** Uno 5V → breadboard + rail, Uno GND → − rail.
2. **OLED.** VCC/GND → rails, SDA → A4, SCL → A5. Flash (`make flash`):
   the HUD boots to "CyclUno ready". The default build drives an SSD1327
   128x128; other panels are one build flag away:

   ```bash
   make flash                                                # SSD1327 128x128
   PLATFORMIO_BUILD_FLAGS=-DDISPLAY_SH1107_128X128  make flash
   PLATFORMIO_BUILD_FLAGS=-DDISPLAY_SSD1306_128X64  make flash   # legacy panels
   PLATFORMIO_BUILD_FLAGS=-DDISPLAY_SSD1306_128X32  make flash
   ```

   The HUD is a 16-row x 16-col text grid; smaller panels just clip to
   their top rows.
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
| OLED dark | wrong controller: rebuild with the other `DISPLAY_*` define; else try addr 0x3D; check A4/A5 not swapped |
| OLED garbled / offset pixels | SSD1327 firmware on an SH1107 panel (or vice versa) — switch the define |
| ghost button presses | missing GND leg — every button must return to the − rail |
| APP mode does nothing on the host | `/dev/uinput` permission: `sudo usermod -aG input $USER`, re-login |
