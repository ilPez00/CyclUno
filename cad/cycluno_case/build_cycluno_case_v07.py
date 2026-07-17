import FreeCAD, Part, math, os

doc = FreeCAD.newDocument("CyclUnoCase_v07")

# ============================================================================
# v0.7 — Palm Deck for the SPI TFT era. Fixes over v0.6:
#   * Rotation() takes DEGREES; v0.6 passed radians -> stick rake was ~0.2 deg.
#   * Display pocket for the 1.44 in ST7735 TFT (square window), not the old
#     30x40 OLED. Module dims are parameterized: MEASURE the real breakout
#     before printing (label: TFT_*).
#   * Sticks offset per FORMFACTOR rule 1: left-lower, right-upper.
#   * Button diamond moved OUT of the joy2 thumb well (v0.6 put buttons at
#     12 mm from stick center with a 12.5 mm well rim).
#   * Uno mounts on 6 mm floor standoffs at the REAL drill pattern, USB-B and
#     barrel-jack wall cutouts on the -X wall.
#   * doc.saveAs at the end (v0.6 never saved -> no FCStd on disk).
# ============================================================================

# ===== REAL COMPONENT DIMS (measure before print where marked) =====
JOY_SHAFT_R = 5.5        # HW-504 shaft clearance radius (hole = R+1)
TFT_PCB_W, TFT_PCB_D = 35.0, 34.0   # MEASURE: common 1.44" ST7735 breakout
TFT_ACT = 27.0                       # window for 25.5x26.5 active area + slack
TFT_HOLE_R = 1.3                     # M2.5 corner holes, MEASURE inset
TFT_HOLE_INSET = 2.5
BTN_FOOT = 6.0
UNO_W, UNO_D = 68.6, 53.4
# Real Arduino Uno drill pattern, mm from board lower-left (USB on -X edge):
UNO_HOLES = [(13.97, 2.54), (66.04, 7.62), (66.04, 35.56), (15.24, 50.80)]
UNO_HOLE_R = 1.6
M3_R = 1.3

# ===== PALM ENVELOPE (avg hand; parameterize with real measurements) =====
PALM_W, PALM_L = 95.0, 105.0
W, D, H = PALM_W + 12.0, PALM_L + 6.0, 38.0   # 107 x 111 x 38
WALL = 2.5

# ===== loft CONTOUR =====
# v0.6 lofted FACES -> Part returned a Shell; every later boolean threw
# "Null shape". Loft WIRES with solid=True.
def profile(w, d, c):
    pts = [FreeCAD.Vector(-w+c,-d), FreeCAD.Vector(w-c,-d), FreeCAD.Vector(w,-d+c),
           FreeCAD.Vector(w,d-c), FreeCAD.Vector(w-c,d), FreeCAD.Vector(-w+c,d),
           FreeCAD.Vector(-w,d-c), FreeCAD.Vector(-w,-d+c), FreeCAD.Vector(-w+c,-d)]
    return Part.makePolygon(pts)

def atZ(wire, z):
    w = wire.copy()
    w.translate(FreeCAD.Vector(0, 0, z))
    return w

SEC = [(W/2*0.82, D/2*0.80, 8.0, 0.0),
       (W/2,      D/2,     12.0, H*0.45),
       (W/2*0.88, D/2*0.86, 8.0, H)]
outer = Part.makeLoft([atZ(profile(s[0], s[1], s[2]), s[3]) for s in SEC], True)
print("loft solid V=", round(outer.Volume/1000, 1))

# Loft profiles are origin-centered; component placement below uses 0..W /
# 0..D coordinates (v0.6 skipped this shift and cut into the wrong quadrant).
outer.translate(FreeCAD.Vector(W/2, D/2, 0))

# ===== hollow: cut the wall-shrunk inner solid from the outer solid =====
inner = outer.makeOffsetShape(-WALL, 1e-4, True, False, 0)
base = outer.cut(inner)
print("hollow V=", round(base.Volume/1000, 1))
# floor cap (close bottom -> pocket)
base = base.fuse(Part.makeBox(W, D, WALL))
print("stage: floor ok V=", round(base.Volume/1000, 1))

# ===== CONTROL LAYOUT (FORMFACTOR rule 1: offset sticks) =====
jx1, jy1 = W*0.28, D*0.32        # left stick, lower-left
jx2, jy2 = W*0.72, D*0.48        # right stick, upper-right
WELL_R, WELL_DEPTH = 16.0, 6.0   # rim radius at surface = sqrt(16^2-10^2) ~ 12.5

# ===== THUMB WELLS (sphere.common, verified in v0.6) =====
def thumb_well(xc, yc, r, depth):
    sph = Part.makeSphere(r).translated(FreeCAD.Vector(xc, yc, H))
    cut = Part.makeBox(2*r, 2*r, depth+2).translated(FreeCAD.Vector(xc-r, yc-r, H-depth))
    return sph.common(cut)

base = base.cut(thumb_well(jx1, jy1, WELL_R, WELL_DEPTH))
base = base.cut(thumb_well(jx2, jy2, WELL_R, WELL_DEPTH))
print("stage: wells ok V=", round(base.Volume/1000, 1))

# ===== JOYSTICK: raked shaft hole + chamfer bezel =====
# Rotation(yaw, pitch, roll) takes DEGREES — v0.6 fed it radians.
# Bezel cone widens the hole so the shaft clears full deflection through the rake.
def joy_mount(xc, yc, tilt_deg):
    rot = FreeCAD.Rotation(0, tilt_deg, 0)
    shaft = Part.makeCylinder(JOY_SHAFT_R+1.0, H+4)
    shaft.Placement = FreeCAD.Placement(FreeCAD.Vector(xc, yc, H/2), rot)
    bez = Part.makeCone(JOY_SHAFT_R+1.0, JOY_SHAFT_R+6.0, 3.0)
    bez.Placement = FreeCAD.Placement(FreeCAD.Vector(xc, yc, H-3.0), rot)
    return shaft.fuse(bez)

base = base.cut(joy_mount(jx1, jy1, 12.0)).cut(joy_mount(jx2, jy2, -12.0))
print("stage: joys ok V=", round(base.Volume/1000, 1))

# ===== TFT: recessed PCB pocket + square glass window + corner posts =====
# D*0.75 keeps the PCB pocket inside the top face (contour narrows toward
# the back; 0.78 overran the footprint by ~1.4 mm).
tx, ty = W*0.5, D*0.75
base = base.cut(Part.makeBox(TFT_PCB_W+2, TFT_PCB_D+2, 6.0)
                .translated(FreeCAD.Vector(tx-TFT_PCB_W/2-1, ty-TFT_PCB_D/2-1, H-6.0)))
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

# ===== BUTTONS: diamond under the right-thumb arc, clear of the joy2 well =====
# Nearest button to joy2 center must stay outside rim (12.5) + foot clearance.
bx0, by0 = W*0.78, D*0.20
bsp = 12.0
for (bx, by) in [(bx0, by0-bsp), (bx0-bsp, by0), (bx0+bsp, by0), (bx0, by0+bsp)]:
    dj = math.hypot(bx-jx2, by-jy2)
    assert dj > 12.5 + BTN_FOOT/2 + 1.0, "button inside joy2 thumb well"
    clr = Part.makeCylinder(BTN_FOOT/2+0.6, H)
    clr.Placement = FreeCAD.Placement(FreeCAD.Vector(bx, by, H/2), FreeCAD.Rotation())
    thr = Part.makeCylinder(2.0, H+4)
    thr.Placement = FreeCAD.Placement(FreeCAD.Vector(bx, by, H/2), FreeCAD.Rotation())
    base = base.cut(clr.fuse(thr))
print("stage: buttons ok V=", round(base.Volume/1000, 1))

# ===== LEDs (REC + LINK), outside the joy1 well rim =====
for (lx, ly) in [(jx1-13, jy1+9), (jx1+13, jy1+9)]:
    h = Part.makeCylinder(2.6, H+2)
    h.Placement = FreeCAD.Placement(FreeCAD.Vector(lx, ly, H/2), FreeCAD.Rotation())
    base = base.cut(h)
print("stage: leds ok V=", round(base.Volume/1000, 1))

# ===== MODE slot =====
# FORMFACTOR wants a 3-pos detent rocker; firmware today reads a momentary
# button on D2. Slot fits either — resolve before final print.
mx, my = W*0.16, D*0.90
base = base.cut(Part.makeBox(22.0, 8.0, 8.0).translated(FreeCAD.Vector(mx-11, my-4, H-8)))
for dx in (-8, 0, 8):
    nub = Part.makeCylinder(1.8, 3.0)
    nub.Placement = FreeCAD.Placement(FreeCAD.Vector(mx+dx, my, H-2), FreeCAD.Rotation())
    base = base.cut(nub)
print("stage: mode ok V=", round(base.Volume/1000, 1))

# ===== UNO on the FLOOR: 6 mm standoffs at the real drill pattern =====
# Board lower-left corner in case coords; USB-B edge faces the -X wall.
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

# ===== -X wall cutouts: USB-B + barrel jack (VERIFY against real board) =====
# Connector centerlines from the Uno's -X board edge, y from board lower-left:
# USB-B ~ y=37.5, barrel jack ~ y=8.0; both bottoms sit ~0 on the PCB top,
# PCB top = WALL + SO_H + 1.6.
pcb_top = WALL + SO_H + 1.6
usb = Part.makeBox(WALL+8.0, 14.0, 12.0).translated(
    FreeCAD.Vector(-4.0, uy0+37.5-7.0, pcb_top))
jack = Part.makeBox(WALL+8.0, 11.0, 12.0).translated(
    FreeCAD.Vector(-4.0, uy0+8.0-5.5, pcb_top))
base = base.cut(usb).cut(jack)

base_obj = doc.addObject("Part::Feature", "Base_v07")
base_obj.Shape = base

# ===== LID (5 mm slab matching the contour's lower taper) =====
# v0.6 clamped all three sections to z<=5, stacking two identical profiles at
# z=5 — invalid for a solid loft. Interpolate the true contour at z=5 instead.
t = 5.0 / SEC[1][3]
lerp = tuple(SEC[0][i] + t*(SEC[1][i] - SEC[0][i]) for i in range(3))
lid = Part.makeLoft([atZ(profile(*SEC[0][:3]), 0.0),
                     atZ(profile(*lerp), 5.0)], True)
lid.translate(FreeCAD.Vector(W/2, D/2, 0))
for (hx, hy) in UNO_HOLES:
    h = Part.makeCylinder(M3_R+0.5, 7.0)
    h.Placement = FreeCAD.Placement(FreeCAD.Vector(ux0+hx, uy0+hy, -1), FreeCAD.Rotation())
    lid = lid.cut(h)
lid_obj = doc.addObject("Part::Feature", "Lid_v07")
lid_obj.Shape = lid

doc.recompute()
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CyclUnoCase_v07.FCStd")
doc.saveAs(out)
print("BASE v07 V=", round(base.Volume/1000, 1), "cm3  z[0,%.0f]" % H)
print("LID  v07 V=", round(lid.Volume/1000, 1), "cm3")
print("joy1@(%.0f,%.0f) joy2@(%.0f,%.0f) TFT@(%.0f,%.0f) btn-diamond@(%.0f,%.0f) MODE@(%.0f,%.0f)"
      % (jx1, jy1, jx2, jy2, tx, ty, bx0, by0, mx, my))
print("uno origin@(%.1f,%.1f) standoffs h=%.0f  saved: %s" % (ux0, uy0, SO_H, out))
