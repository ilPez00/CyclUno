# CyclUno — Form Factor Spec (aion control deck)

Design thesis for the physical enclosure. Grounded in the aion cockpit nav
model (see `aion/src/aion/`) and HCI precedent for split dual-thumbstick
one-handed consoles (Steam Controller / Xbox Adaptive / FragChuck lineage).

## 1. What the deck IS

CyclUno is the **aion control deck**: a two-thumb, one-handed cockpit console.
- **joy1 (left thumb)** = primary navigation: up/down scroll lists, left/right (or
  SW click) = switch workspace (13 workspaces, wraps modulo).
- **joy2 (right thumb)** = activate/context in AION mode; analog axes in APP mode
  (uinput "CyclUno Pad" gamepad).
- **Buttons**: A=activate/REC, B=back/menu, MODE=AION⇄APP toggle, X/Y=context.
- **OLED (128×128, 16×16 text grid)** = status compass: always show WORKSPACE
  NAME + 1-line context (top row), since 13 workspaces need constant orientation.
- **MODE** must be a physical slide/rocker with detent, NOT a held button
  (context flip you can feel without looking).

## 2. Ergonomic rules (from HCI precedent)

1. **Offset symmetric thumbsticks, not collinear.** Steam/Xbox layout is proven
   best for simultaneous dual-thumb use without hand cramp. Two HW-504 sticks
   sit at ~45° offset (left-lower, right-upper), like a Steam Controller —
   NOT side-by-side flat.
2. **Thumbs own the whole interaction.** joy1 does list-scroll AND workspace-switch;
   it needs a click (SW=activate) + 4 directions. No finger-reassignment mid-flow.
3. **Mode = detent rocker.** AION⇄APP is a context flip; a 3-pos rocker
   (AION / OFF / APP) you feel, prevents accidental gamepad-vs-cockpit mode.
4. **OLED as status compass, not a screen.** 128×128 = 16×16 text. Top row =
   workspace + context. This is the "where am I" anchor.
5. **One-handed grip envelope.** Fits a relaxed palm, both thumbs on sticks.
   Target ~90–110mm wide, ~60–70mm deep, contoured to palm.

## 3. Highest-frequency action = workspace switch

13 workspaces (desktop, models, tasks, agent, memory, vault, sys, hermes,
skills, projects, term, swarm, settings). joy1-left/right → `switch_workspace`
is the most-used nav action — keep it on the PRIMARY thumb, low-friction,
non-mode. Current protocol already maps joy1 L/R → switch_workspace. **Keep it.**

## 4. Recommended form factor — TIER A: "Palm Deck"

Evolve the enclosure from a rectangular breadboard box into a contoured controller:

- Contoured underside (fits palm); flat-ish top face.
- **Offset thumbsticks**: left stick lower-left ~30° rake, right stick upper-right.
- **MODE rocker** (3-pos AION/OFF/APP) with detent, on the top edge.
- **OLED** top-center as status compass.
- **4 buttons as a diamond** under the right-thumb arc: A bottom, B left, X right, Y top.
- Grip edges rounded (R~15mm corners), not a sharp rectangle.

## 5. TIER B (interim): "Dockable Slab"

What v0.2 already is, upgraded:
- Keep 94×66 rectangular case + breadboard standoffs.
- Rake the two stick cutouts (not parallel).
- Add MODE rocker slot.
- OLED top-row workspace label (cutout already in v0.1).

Good for desktop; less ideal handheld. This is the pragmatic step while Tier A
is prototyped.

## 6. CAD evolution map

| Ver | Form | State |
|-----|------|-------|
| v0.1 | rectangular slab, OLED+stick+button holes | built, saved |
| v0.2 | slab + 4 standoffs + screw-on lid | built, committed (14bae91) |
| v0.3 | TIER B slab: raked sticks + MODE slot + rounded grip (coordinate-placed, NOT ergo-derived) | built, committed (ae5e340) — DEV ENCLOSURE, not final form |
| v0.4 | TIER A Palm Deck — layout DERIVED from hand envelope (thumb-pad centers, sight-line OLED, detent MODE) | built, committed — hand metrics are AVG (parameterize w/ real) |
| v0.5 | contoured shell + real-component holes | built, committed (b122cbe) |
| v0.6 | thumb wells + counterbores + Uno standoffs | script only — never produced an FCStd: face-loft returned a Shell (booleans die), no `saveAs`, layout cut in the wrong quadrant, stick rake passed radians to a degrees API, buttons landed inside the joy2 well, display pocket still OLED |
| v0.7 | TFT-era redesign: solid loft + hollow-by-cut, first-quadrant layout, offset sticks (rule 1), button diamond clear of wells, real Uno drill pattern on 6 mm floor standoffs, USB-B + jack wall cutouts, square ST7735 window, saveAs | built, FCStd saved — TFT module dims are PLACEHOLDERS, measure before print |

> **Honesty note (v0.3):** the cutouts are coordinate-placed against a rectangle, not
> derived from thumb-reach. It protects the breadboard and proves the cutout *set*,
> but it is NOT ergonomic. v0.4 must derive hole positions from a palm-grip
> envelope, not from `makeBox` guesses.

## 7. Open fits to verify (before print)

- Real stacked height of breadboard + Uno (standoff height depends on it).
- Exact control positions once components are placed on the breadboard.
- HW-504 stick shaft travel vs rake angle (rake changes shaft clearance).
- OLED module bezel vs cutout (30×30 window in v0.1).
