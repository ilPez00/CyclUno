import FreeCAD, Part, math, os

doc = FreeCAD.newDocument("CyclUnoCase_v09")

# ============================================================================
# v0.9 — v0.8 + PROPER LID MOUNTING. v0.8 reused the asymmetric Arduino drill
# pattern (UNO_HOLES) for the lid screws, so the "screw holes" were off-center
# and wrongly spaced (and read as bottom holes). v0.9 adds 4 SYMMETRIC corner
# screw posts, evenly inset from each corner, tapped in the base and
# counterbored in the lid so the lid seats flush on top. M3 self-tap.
# ============================================================================
# v0.8 basis — FINAL ergonomic Palm Deck. Dimensions reconciled against the REAL
# component STEP models pulled into cad/components/ (measured 2026-07-17):
#   * Tact switch SW_PUSH_6mm_H5mm : body 7.2 x 6.0, H 8.5  -> BTN_FOOT 7.2
#   * LED_D5.0mm                   : dia 5.4, H 14.1        -> LED hole R 2.8
#   * PinHeader_1x08 vertical      : 2.5 x 20.3, H 11.5     -> TFT header stack
#     clearance: the TFT breakout sits on an 11.5 mm header, so the PCB pocket
#     must recess deep enough that the glass still reaches the top face.
#   * Arduino_Uno.step is a partial KiCad connector model (19.7x25.9), NOT the
#     full board outline -> board footprint stays the datasheet 68.6 x 53.4.
# Geometry pipeline (loft WIRES solid=True -> offset hollow -> boolean cuts)
# is unchanged from v0.7 which produced a valid manifold solid.
# ============================================================================

# ===== REAL COMPONENT DIMS (from pulled STEP models) =====
JOY_SHAFT_R = 5.5            # HW-504 shaft clearance radius (hole = R+1)
TFT_PCB_W, TFT_PCB_D = 35.0, 34.0    # 1.44" ST7735 breakout PCB
TFT_ACT = 27.0                       # glass window (25.5x26.5 active + slack)
TFT_HOLE_R = 1.3                     # M2.5 corner mount holes
TFT_HOLE_INSET = 2.5
TFT_HEADER_H = 11.5                  # measured: 1x08 vertical header height
BTN_FOOT = 7.2                       # measured tact switch body width
BTN_PLUNGER_R = 2.0                  # cap stem clearance
LED_DIA = 5.4                        # measured LED body diameter
LED_R = LED_DIA/2 + 0.1             # print clearance -> 2.8
UNO_W, UNO_D = 68.6, 53.4           # datasheet board outline (STEP is partial)
UNO_HOLES = [(13.97, 2.54), (66.04, 7.62), (66.04, 35.56), (15.24, 50.80)]
UNO_HOLE_R = 1.6
M3_R = 1.3

# ===== PALM ENVELOPE =====
PALM_W, PALM_L = 95.0, 105.0
W, D, H = PALM_W + 12.0, PALM_L + 6.0, 38.0   # 107 x 111 x 38
WALL = 2.5

# ===== loft CONTOUR (WIRES, solid=True) =====
def profile(w, d, c):
    pts = [FreeCAD.Vector(-w+c,-d), FreeCAD.Vector(w-c,-d), FreeCAD.Vector(w,-d+c),
           FreeCAD.Vector(w,d-c), FreeCAD.Vector(w-c,d), FreeCAD.Vector(-w+c,d),
           FreeCAD.Vector(-w,d-c), FreeCAD.Vector(-w,-d+c), FreeCAD.Vector(-w+c,-d)]
    return Part.makePolygon(pts)

def atZ(wire, z):
    w = wire.copy(); w.translate(FreeCAD.Vector(0, 0, z)); return w

SEC = [(W/2*0.82, D/2*0.80, 8.0, 0.0),
       (W/2,      D/2,     12.0, H*0.45),
       (W/2*0.88, D/2*0.86, 8.0, H)]
outer = Part.makeLoft([atZ(profile(s[0], s[1], s[2]), s[3]) for s in SEC], True)
print("loft solid V=", round(outer.Volume/1000, 1))
outer.translate(FreeCAD.Vector(W/2, D/2, 0))

# ===== hollow =====
inner = outer.makeOffsetShape(-WALL, 1e-4, True, False, 0)
base = outer.cut(inner)
base = base.fuse(Part.makeBox(W, D, WALL))     # floor cap
print("stage: floor ok V=", round(base.Volume/1000, 1))

# ===== CONTROL LAYOUT (offset sticks, rule 1) =====
jx1, jy1 = W*0.28, D*0.32        # left stick, lower-left
jx2, jy2 = W*0.72, D*0.48        # right stick, upper-right
WELL_R, WELL_DEPTH = 16.0, 6.0

def thumb_well(xc, yc, r, depth):
    sph = Part.makeSphere(r).translated(FreeCAD.Vector(xc, yc, H))
    cut = Part.makeBox(2*r, 2*r, depth+2).translated(FreeCAD.Vector(xc-r, yc-r, H-depth))
    return sph.common(cut)

base = base.cut(thumb_well(jx1, jy1, WELL_R, WELL_DEPTH))
base = base.cut(thumb_well(jx2, jy2, WELL_R, WELL_DEPTH))
print("stage: wells ok V=", round(base.Volume/1000, 1))

# ===== JOYSTICK: raked shaft hole + chamfer bezel (Rotation in DEGREES) =====
def joy_mount(xc, yc, tilt_deg):
    rot = FreeCAD.Rotation(0, tilt_deg, 0)
    shaft = Part.makeCylinder(JOY_SHAFT_R+1.0, H+4)
    shaft.Placement = FreeCAD.Placement(FreeCAD.Vector(xc, yc, H/2), rot)
    bez = Part.makeCone(JOY_SHAFT_R+1.0, JOY_SHAFT_R+6.0, 3.0)
    bez.Placement = FreeCAD.Placement(FreeCAD.Vector(xc, yc, H-3.0), rot)
    return shaft.fuse(bez)

base = base.cut(joy_mount(jx1, jy1, 12.0)).cut(joy_mount(jx2, jy2, -12.0))
print("stage: joys ok V=", round(base.Volume/1000, 1))

# ===== TFT: recessed PCB pocket sized for the 11.5 mm header stack =====
# Pocket floor must sit low enough that glass on top of the header reaches the
# top face. Pocket depth = header + PCB(1.6) + glass(1.6) clearance ~ 6 mm.
tx, ty = W*0.5, D*0.75
POCKET_D = 6.0
base = base.cut(Part.makeBox(TFT_PCB_W+2, TFT_PCB_D+2, POCKET_D)
                .translated(FreeCAD.Vector(tx-TFT_PCB_W/2-1, ty-TFT_PCB_D/2-1, H-POCKET_D)))
base = base.cut(Part.makeBox(TFT_ACT, TFT_ACT, 4.0)
                .translated(FreeCAD.Vector(tx-TFT_ACT/2, ty-TFT_ACT/2, H-4.0)))
for sx in (-1, 1):
    for sy in (-1, 1):
        hx = tx + sx*(TFT_PCB_W/2 - TFT_HOLE_INSET)
        hy = ty + sy*(TFT_PCB_D/2 - TFT_HOLE_INSET)
        h = Part.makeCylinder(TFT_HOLE_R, 8.0)
        h.Placement = FreeCAD.Placement(FreeCAD.Vector(hx, hy, H-8), FreeCAD.Rotation())
        base = base.cut(h)
print("stage: tft ok V=", round(base.Volume/1000, 1))

# ===== BUTTONS: diamond under right-thumb arc, real 7.2 mm foot =====
bx0, by0 = W*0.78, D*0.20
bsp = 12.0
for (bx, by) in [(bx0, by0-bsp), (bx0-bsp, by0), (bx0+bsp, by0), (bx0, by0+bsp)]:
    dj = math.hypot(bx-jx2, by-jy2)
    assert dj > 12.5 + BTN_FOOT/2 + 1.0, "button inside joy2 thumb well"
    clr = Part.makeCylinder(BTN_FOOT/2+0.6, H)   # 4.2 R recess for switch body
    clr.Placement = FreeCAD.Placement(FreeCAD.Vector(bx, by, H/2), FreeCAD.Rotation())
    thr = Part.makeCylinder(BTN_PLUNGER_R, H+4)
    thr.Placement = FreeCAD.Placement(FreeCAD.Vector(bx, by, H/2), FreeCAD.Rotation())
    base = base.cut(clr.fuse(thr))
print("stage: buttons ok V=", round(base.Volume/1000, 1))

# ===== LEDs (REC + LINK), real 5.4 mm dia, outside joy1 rim =====
for (lx, ly) in [(jx1-13, jy1+9), (jx1+13, jy1+9)]:
    h = Part.makeCylinder(LED_R, H+2)
    h.Placement = FreeCAD.Placement(FreeCAD.Vector(lx, ly, H/2), FreeCAD.Rotation())
    base = base.cut(h)
print("stage: leds ok V=", round(base.Volume/1000, 1))

# ===== MODE slot =====
mx, my = W*0.16, D*0.90
base = base.cut(Part.makeBox(22.0, 8.0, 8.0).translated(FreeCAD.Vector(mx-11, my-4, H-8)))
for dx in (-8, 0, 8):
    nub = Part.makeCylinder(1.8, 3.0)
    nub.Placement = FreeCAD.Placement(FreeCAD.Vector(mx+dx, my, H-2), FreeCAD.Rotation())
    base = base.cut(nub)
print("stage: mode ok V=", round(base.Volume/1000, 1))

# ===== UNO on the FLOOR: 6 mm standoffs at the real drill pattern =====
SO_H = 6.0
ux0, uy0 = W*0.5 - UNO_W/2, D*0.10
for (hx, hy) in UNO_HOLES:
    x, y = ux0 + hx, uy0 + hy
    so = Part.makeCylinder(3.5, SO_H)
    so.Placement = FreeCAD.Placement(FreeCAD.Vector(x, y, WALL), FreeCAD.Rotation())
    hole = Part.makeCylinder(M3_R, SO_H+2)
    hole.Placement = FreeCAD.Placement(FreeCAD.Vector(x, y, WALL-1), FreeCAD.Rotation())
    base = base.fuse(so.cut(hole))
print("stage: standoffs ok V=", round(base.Volume/1000, 1))

# ===== -X wall cutouts: USB-B + barrel jack =====
pcb_top = WALL + SO_H + 1.6
usb = Part.makeBox(WALL+8.0, 14.0, 12.0).translated(
    FreeCAD.Vector(-4.0, uy0+37.5-7.0, pcb_top))
jack = Part.makeBox(WALL+8.0, 11.0, 12.0).translated(
    FreeCAD.Vector(-4.0, uy0+8.0-5.5, pcb_top))
base = base.cut(usb).cut(jack)

# ===== LID SCREW POSTS: 4 symmetric corner bosses, tapped for M3 self-tap =====
# Centered/evenly spaced: same inset from each corner in X and Y, so the four
# holes form a centered rectangle. Posts rise from the floor to just under the
# top face; the lid screws down into them from the top.
POST_INSET = 9.0            # centerline inset from each outer wall/corner
POST_R     = 4.0            # boss outer radius
POST_TAP_R = 1.35          # M3 self-tap pilot (~2.7 mm dia)
POST_TOP   = H - 5.0        # posts stop 5 mm below top -> lid slab sits on them
LID_SCREW_XY = [(POST_INSET,        POST_INSET),
                (W - POST_INSET,    POST_INSET),
                (W - POST_INSET,    D - POST_INSET),
                (POST_INSET,        D - POST_INSET)]
for (x, y) in LID_SCREW_XY:
    boss = Part.makeCylinder(POST_R, POST_TOP - WALL)
    boss.Placement = FreeCAD.Placement(FreeCAD.Vector(x, y, WALL), FreeCAD.Rotation())
    pilot = Part.makeCylinder(POST_TAP_R, POST_TOP)   # blind-ish tap from top
    pilot.Placement = FreeCAD.Placement(FreeCAD.Vector(x, y, WALL + 2.0), FreeCAD.Rotation())
    base = base.fuse(boss).cut(pilot)
print("stage: lid-posts ok V=", round(base.Volume/1000, 1))

base_obj = doc.addObject("Part::Feature", "Base_v09")
base_obj.Shape = base

# ===== LID (5 mm contoured slab) =====
t = 5.0 / SEC[1][3]
lerp = tuple(SEC[0][i] + t*(SEC[1][i] - SEC[0][i]) for i in range(3))
lid = Part.makeLoft([atZ(profile(*SEC[0][:3]), 0.0),
                     atZ(profile(*lerp), 5.0)], True)
lid.translate(FreeCAD.Vector(W/2, D/2, 0))
# 4 centered corner screw holes matching the base posts, counterbored for
# M3 pan/countersunk heads so they seat flush with the lid top.
SCREW_CLEAR_R = 1.7        # M3 shank clearance (~3.4 mm dia)
CBORE_R       = 3.2        # counterbore for M3 head
CBORE_DEPTH   = 2.5
for (x, y) in LID_SCREW_XY:
    thru = Part.makeCylinder(SCREW_CLEAR_R, 8.0)
    thru.Placement = FreeCAD.Placement(FreeCAD.Vector(x, y, -1), FreeCAD.Rotation())
    cbore = Part.makeCylinder(CBORE_R, CBORE_DEPTH + 1)
    cbore.Placement = FreeCAD.Placement(FreeCAD.Vector(x, y, 5.0 - CBORE_DEPTH), FreeCAD.Rotation())
    lid = lid.cut(thru).cut(cbore)
lid_obj = doc.addObject("Part::Feature", "Lid_v09")
lid_obj.Shape = lid

doc.recompute()
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CyclUnoCase_v09.FCStd")
doc.saveAs(out)
print("BASE v09 V=", round(base.Volume/1000, 1), "cm3  z[0,%.0f]" % H, "watertight=", base.isValid())
print("LID  v09 V=", round(lid.Volume/1000, 1), "cm3  valid=", lid.isValid())
print("lid screw holes (centered rect):", LID_SCREW_XY)
print("saved:", out)
