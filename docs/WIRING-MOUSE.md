# CyclUno — mouse controller

One joystick (pointer + left click), one button (right click), one MPU6050
(gesture macros). No display.

## Pin map

| Part | Signal | Uno pin |
|------|--------|:-------:|
| HW-504 joystick | VRy (Y axis) | A0 |
| ^ | VRx (X axis) | A1 |
| ^ | SW (push) | D2 |
| Tactile button | SIG → GND (INPUT_PULLUP) | D3 |
| HW-123 (MPU6050) | VCC | 5V |
| ^ | GND | GND |
| ^ | SDA | A4 |
| ^ | SCL | A5 |
| ^ | AD0 | GND (I2C addr 0x68) |

No VCC on button or joystick switch — Uno internal pullup drives HIGH;
pressing shorts to GND → reads LOW.

## HW-123 / MPU6050

The breakout has a regulator — feed **5V**. I2C address **0x68** (AD0 to GND).

## Interaction model

| Input | Action | Output |
|-------|--------|--------|
| Joystick move | Pointer moves (velocity curve) | `M dx dy` |
| Joystick push | Left click | `L 0/1` |
| Button push | Right click | `R 0/1` |
| Tilt left (`roll > 30°`) | Wheel down | `W -1` |
| Tilt right (`roll < -30°`) | Wheel up | `W 1` |
| Nod (pitch oscillation) | Macro 1 | `G 1` |
| Shake (lateral oscillation) | Macro 2 | `G 2` |
| Left double-click | Macro 4 | `G 4` |
| Left long-press | Macro 5 | `G 5` |
| Right double-click | Macro 6 | `G 6` |
| Right long-press | Macro 7 | `G 7` |

The velocity curve maps small joystick deflections to fine sub-pixel moves
and large deflections to fast cursor movement via a sqrt-like curve.
Deadzone of ±20 ADC counts prevents drift.

## Bring-up

1. Wire GND rail first.
2. Joystick: A0, A1, D2, +5V, GND.
3. Button: D3 to one leg, other leg to GND.
4. MPU6050: 5V, GND, A4, A5.
5. Flash diag: `make diag` — verify all values live.
6. Flash main: `make flash` — open serial, move joystick, see `M -3 12` etc.

## Diagnostic output

```
WHOAMI=0x68 (MPU detected)
JOY_Y,JOY_X,SW|BTN|ax,ay,az|gx,gy,gz|pitch,roll
512,512,0|0|156,-2048,16384|12,-4,3|0,0
```

Resting: JOY ~512 center, SW=0/BTN=0 (released). IMZ: az≈16384 (gravity),
pitch/roll near 0. Move/tilt everything — values track live.

## Main firmware output

```
I 1
M 0 5
M -3 12
L 1
L 0
R 1
R 0
G 1
W -1
```

Host parser reads one line per event. Space-delimited: `type [arg1 [arg2]]`.

## Build

```bash
make test      # host gate (HUD + joystick + deck logic)
make build     # pio run -e cycluno
make flash     # pio run -e cycluno -t upload
make diag      # flash + monitor the wiring diagnostic
```

## Troubleshooting

| Symptom | Check |
|---------|-------|
| No serial output | USB connected? Monitor baud = 115200? |
| Pointer drifts | Deadzone too small; check JOY ~512 at rest in diag |
| No left click | D2 wire; pinMode INPUT_PULLUP; SW→GND |
| No right click | D3 wire; other leg to GND |
| MPU6050 not found | SDA→A4, SCL→A5, 5V, GND, AD0→GND |
| No wheel/gestures | IMU not detected or gyro thresholds too high |
| Gestures fire randomly | THRESH too low in code; adjust per your board |
