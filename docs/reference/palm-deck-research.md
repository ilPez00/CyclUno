# Palm-deck research compendium (2026-07-17)

Deep-research harvest for the CyclUno Palm Deck redesign (case v0.7+).
Method: 5-angle web sweep → source fetch → adversarial 3-vote verification.
Two runs both hit session limits mid-verify, so only the first claims carry a
**VERIFIED 3-0** stamp; the rest are **source-cited but unverified** — treat as
strong leads, confirm against the physical part before cutting plastic.
Sources are condensed here per the cross-project research-mirror rule; URL per
claim, no verbatim doc mirrors.

## 1. Display — 1.44″ ST7735 128×128 SPI breakout

| Fact | Status | Source |
|---|---|---|
| MSP1443 PCB **29.7 × 43.36 mm**, active area **26.2 × 27.2 mm**, 128×128 | VERIFIED 3-0 | lcdwiki.com `1.44inch_SPI_Module_ST7735S_SKU:MSP1443` |
| VCC accepts 3.3–5 V, but logic IO is **3.3 V TTL** → level-shift from 5 V Uno GPIO | VERIFIED 3-0 | same |
| Manual has **no mounting-hole pattern / mechanical drawing** — measure the real module | VERIFIED 3-0 | lcdwiki MSP1443 user manual PDF |
| VCC pin can take Uno 5 V rail directly (onboard regulation) | VERIFIED 3-0 | same |
| 8-pin single-row header (VCC GND CS RESET A0 SDA SCK LED) along one edge; LED active-high, tie to 3.3 V for always-on | unverified | lcdwiki MSP1443 |
| Sibling SKU MAR1441 (Arduino shield form): PCB 31.49 × 43.95 mm, same 26.2 × 27.2 active area | unverified | lcdwiki MAR1441 |
| displaymodule.com panel: active 25.50 × 26.50 mm; bare ST7735S panel is 2.8 V — 5 V safety depends entirely on breakout circuitry | unverified | displaymodule.com DM-TFT144-399 |
| Vendor manual wires logic pins straight to 5 V Uno GPIO with no shifter (vendor practice, not proof of safety) | unverified | lcdwiki manual |

**Design consequence:** WIRING.md's level-shift rule stands (verified 3.3 V TTL
IO). Case v0.7 TFT params updated to MSP1443 dims; active-area offset within
the PCB is undocumented — measure before final print.

## 2. Thumbstick — HW-504 / KY-023

| Fact | Status | Source |
|---|---|---|
| KY-023-style module ≈ **34 × 26 × 32 mm**, four **M4** mounting holes, 5-pin header | unverified | handsontec PS2-Joystick.pdf |
| HW-504 overall ≈ 40 × 26 × 32 mm (footprint + stick height) | unverified | docs.cirkitdesigner.com HW-504 |
| Runs on 5 V; each axis rests ~2.5 V mid-rail, full swing 0–5 V — no shifting needed | unverified | handsontec |
| Joy-IT KY-023 datasheet contains **zero mechanical data** | unverified | naylampmechatronics KY-023 PDF |
| Thingiverse KY-023 mockup models place the stick's rotation point at origin, purpose-built for testing rake angles in enclosure CAD | unverified | thingiverse.com thing:7014864 |
| Two-half printed shell around KY-023 is a proven community pattern | unverified | makerworld.com model 1556892 |

**Design consequence:** no authoritative shaft-travel spec exists — the 12°
rake clearance must be validated with the Thingiverse rotation-origin mockup or
the physical part. STEP model already in `cad/components/hw504_joystick/`
(dir present, file pending).

## 3. Ergonomics — one-handed dual-stick controllers

Fetches for this angle (researchgate, access-ability.uk, instructables) died on
rate limits in both runs — **no citable claims landed**. FORMFACTOR.md §2 keeps
its Steam-Controller-lineage heuristics (offset sticks, thumb-arc diamond,
90–110 mm palm width) as design priors, not cited fact. Re-run this angle later
or validate by printed prototype.

## 4. MODE selector — 3-position part + AVR reading

| Fact | Status | Source |
|---|---|---|
| **MTS-103**: SPDT mini toggle, **ON-OFF-ON** (center detent off) — matches AION/OFF/APP | unverified | handsontec MTS103 PDF |
| Panel-mount **M6×0.75** bushing, 9.5 mm thread height, ~6 mm panel hole + optional 2.4 mm anti-rotation keyway at 6.4 mm offset | unverified | same |
| Solder-lug termination (4.7 mm spacing) — **not breadboard-friendly**, needs flying leads | unverified | same |
| Generic 3-pos slide switch = SP3T: 1 common + 3 position pins | unverified | docs.cirkitdesigner.com 3-position-switch |
| AVR pattern: each position pin `INPUT_PULLUP`, common to GND, active-low reads | unverified | same |

**Design consequence (cycle-4 decision):** breadboard dev unit keeps the
momentary MODE button on D2 (MTS-103 can't sit in a breadboard). The Palm Deck
enclosure adopts the MTS-103: case v0.7 MODE cutout is now an M6 hole +
keyway. Firmware 3-pos support (D2 + A5, both `INPUT_PULLUP`, center-off =
neither low) is **deferred**: the input-event protocol is pinned byte-for-byte
to aion's `deck/protocol.py` (mode codes 0/1 only), so adding an OFF state is
a cross-repo change to coordinate with aion first.

## 5. FDM enclosure practice

| Fact | Status | Source |
|---|---|---|
| Min wall 2 mm (CyclUno's 2.5 mm OK) | unverified | hubs.com enclosure guide |
| Component cavities: +0.5 mm clearance all around | unverified | same |
| Screw holes: clearance = nominal +0.25 mm dia; self-tap = nominal −0.25 mm dia | unverified | same |
| Boss wall ≥ 1× hole dia (M3 boss ≈ 3 mm surrounding wall); ribs 75–80 % of wall | unverified | same |

**Design consequence:** case v0.7 updated — standoff self-tap holes 2.75 mm dia,
lid clearance holes 3.25 mm dia, standoff bosses widened to meet the 1×-dia
rule, pockets carry 0.5 mm clearance.

## Rerun note

Verification infra hit session limits twice (11:10 + 16:30 resets). 4 claims
verified, ~20 cited-unverified, ergonomics angle empty. If a claim here turns
load-bearing, re-verify it manually against the linked source.
