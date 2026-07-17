# CyclUno deck — SPI 128×128 TFT assembly & wiring

CyclUno now targets the connected display: a **128×128 SPI TFT**, assumed to be the common **1.44-inch ST7735** module. The exposed `RES`, `DC`, `CS`, and `BL` pins mean this is not the former I2C OLED design. The sketch uses hardware SPI and `Adafruit_ST7735`.

> Controller check: firmware is for ST7735 128×128. If its PCB/flex says ST7789, ILI9163, or another controller, pause before flashing: the wiring is similar but initialization needs adjustment.

## Critical electrical rule

An Arduino Uno is **5 V logic**. Most bare TFT panels are **3.3 V-only**, both power and signal.

- Feed TFT **VCC from 3.3 V**, unless its breakout explicitly says `5V`, `5V tolerant`, or documents regulator/level shifting.
- Feed `SCK`, `MOSI`, `CS`, and `DC` through a proper 5 V → 3.3 V level shifter unless board documentation explicitly guarantees 5 V-safe inputs.
- Join all grounds: Uno GND ↔ level-shifter GND ↔ TFT GND.
- Never power a 3.3 V-only panel from Uno 5 V.

## Display wiring

| TFT label | Connect to | Meaning |
|---|---|---|
| GND | Uno GND | common ground |
| VCC | 3.3 V* | panel logic/power |
| SCL / SCK / CLK | Uno D13 via level shifter* | SPI clock |
| SDA / MOSI / DIN | Uno D11 via level shifter* | SPI data to TFT |
| CS | Uno D10 via level shifter* | chip select |
| DC / A0 | Uno D9 via level shifter* | data/command select |
| RES / RST | 3.3 V through 10 kΩ | reset held released; **never floating** |
| BL / LED | 3.3 V / VCC only as module specifies | backlight enable/power |

*Level shifting is mandatory unless the breakout explicitly guarantees 5 V-safe signal inputs.

`BL` is not a Uno GPIO here. Most TFT breakouts include its LED resistor, so use the board-specified VCC/3.3 V rail. If BL is a bare LED input, use its datasheet-specified resistor; never assume it is safe at 5 V.

## CyclUno pin map

| Signal | Uno pin |
|---|---:|
| TFT MOSI / SDA | D11 |
| TFT SCK / SCL | D13 |
| TFT CS | D10 |
| TFT DC | D9 |
| TFT RES | no Uno pin; 3.3 V via 10 kΩ |
| TFT BL | 3.3 V/VCC per board |
| Joy1 VRy / VRx / SW | A0 / A1 / D4 |
| Joy2 VRy / VRx / SW | A2 / A3 / D8 |
| Button B | D5 |
| Button MODE | D2 |
| Button X | D3 |
| Button Y | D12 |
| REC / LINK LEDs | D6 / D7 |
| APP LED | A4 external (D13 is TFT clock; do not use its onboard LED as a mode indicator) |

The display consumes D9/D10/D11/D13; MODE and X move from the old layout to **D2/D3**. Buttons wire from their listed pin to GND: firmware uses `INPUT_PULLUP`.

## Bring-up order

1. Wire TFT GND, safe 3.3 V, then SPI/control lines. Keep SPI wiring short.
2. Add `RES → 10 kΩ → 3.3 V`.
3. Wire BL only after checking the module label/datasheet.
4. Flash: `make build && make flash`.
5. Expect status HUD. If blank, recheck common ground, safe voltage/level shifting, and controller identity.
6. Add joy1, B, LEDs, joy2, then MODE/X/Y.

## Build

```bash
make test
make build
make flash
```

## Troubleshooting

| Symptom | Check |
|---|---|
| Blank but backlight on | SCK D13, MOSI D11, CS D10, DC D9; common GND; RES pull-up; correct ST7735 controller |
| White / unstable screen | 5 V signal risk or no level shifting; power down and verify voltage rating |
| Lit, garbled display | controller is not ST7735 or SPI labels swapped |
| No backlight | BL behavior differs by breakout; consult board docs; do not inject 5 V |
| MODE/X do nothing | They moved to D2/D3 |

The former I2C OLED layout (A4/A5, SSD1327/SH1107) is removed from this firmware revision.
