import FreeCAD, Part, math, os

# ============================================================================
# CyclUnoCase v10 — CORRECTED SPLIT: Tray + TopShell
# ============================================================================
# Tray: open-top floor + perimeter walls, Arduino Uno mounts on standoffs
# TopShell: ergonomic contoured palm-shaped upper half, open bottom, carries
#           all controls (joysticks, buttons, LEDs, TFT, MODE slot, thumb wells)
# Mounting: 4 symmetric corner screw bosses tapped in the tray; top shell has
#           counterbored holes so screws go DOWNWARD from the top into the tray.
#           Holes form a centered rectangle: equal inset from all 4 sides.
# ============================================================================

doc = FreeCAD.newDocument("CyclUnoCase_v10")

# ===== REAL COMPONENT DIMS (from pulled STEP models) =====
JOY_SHAFT_R = 5.5            # HW-504 shaft clearance radius (hole = R+1)
TFT_PCB_W, TFT_PCB_D = 35.0, 34.0    # 1.44" ST7735 breakout PCB
TFT_ACT = 27.0                       # glass window (25.5x26.5 active + slack)
TFT_HOLE_R = 1.3                     # M2.5 corner mount holes
TFT_HOLE_INSET = 2.5
BTN_FOOT = 7.2                       # measured tact switch body width
BTN_PLUNGER_R = 2.0                  # cap stem clearance
LED_DIA = 5.4                        # measured LED body diameter
LED_R = LED_DIA/2 + 0.1             # print clearance -> 2.8
UNO_W, UNO_D = 68.6, 53.4           # datasheet board outline
UNO_HOLES = [(13.97, 2.54), (66.04, 7.62), (66.04, 35.56), (15.24, 50.80)]
UNO_HOLE_R = 1.6
M3_R = 1.3

# ===== PALM ENVELOPE =====
PALM_W, PALM_L = 95.0, 105.0
W, D, H = PALM_W + 12.0, PALM_L + 6.0, 38.0   # 107 x 111 x 38
WALL = 2.5

# ===== loft CONTOUR WIRES (solid=True) =====
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

# ===== TOP SHELL (ergonomic upper half, open bottom) =====
top = Part.makeLoft([atZ(profile(s[0], s[1], s[2]), s[3]) for s in SEC], True)
top.translate(FreeCAD.Vector(W/2, D/2, 0))
print("top shell V=", round(top.Volume/1000, 1))

# Carve controls into the top shell (all shallow pockets)
# Thumb wells (spherical cutouts)
jx1, jy1 = W*0.28, D*0.32        # left stick, lower-left
jx2, jy2 = W*0.72, D*0.48        # right stick, upper-right
WELL_R, WELL_DEPTH = 16.0, 6.0
def thumb_well(xc, yc, r, depth):
    sph = Part.makeSphere(r).translated(FreeCAD.Vector(xc, yc, H))
    cut = Part.makeBox(2*r, 2*r, depth+2).translated(FreeCAD.Vector(xc-r, yc-r, H-depth))
    return sph.common(cut)

top = top.cut(thumb_well(jx1, jy1, WELL_R, WELL_DEPTH))
top = top.cut(thumb_well(jx2, jy2, WELL_R, WELL_DEPTH))
print("stage: top wells ok V=", round(top.Volume/1000, 1))

# Joystick raked holes + bezel
def joy_mount(xc, yc, tilt_deg):
    rot = FreeCAD.Rotation(0, tilt_deg, 0)
    shaft = Part.makeCylinder(JOY_SHAFT_R+1.0, H+4)
    shaft.Placement = FreeCAD.Placement(FreeCAD.Vector(xc, yc, H/2), rot)
    bez = Part.makeCone(JOY_SHAFT_R+1.0, JOY_SHAFT_R+6.0, 3.0)
    bez.Placement = FreeCAD.Placement(FreeCAD.Vector(xc, yc, H-3.0), rot)
    return shaft.fuse(bez)

top = top.cut(joy_mount(jx1, jy1, 12.0)).cut(joy_mount(jx2, jy2, -12.0))
print("stage: top joys ok V=", round(top.Volume/1000, 1))

# TFT pocket sized for 11.5mm header stack
tx, ty = W*0.5, D*0.75
POCKET_D = 6.0
top = top.cut(Part.makeBox(TFT_PCB_W+2, TFT_PCB_D+2, POCKET_D)
              .translated(FreeCAD.Vector(tx-TFT_PCB_W/2-1, ty-TFT_PCB_D/2-1, H-POCKET_D)))
top = top.cut(Part.makeBox(TFT_ACT, TFT_ACT, 4.0)
              .translated(FreeCAD.Vector(tx-TFT_ACT/2, ty-TFT_ACT/2, H-4.0)))
for sx in (-1, 1):
    for sy in (-1, 1):
        hx = tx + sx*(TFT_PCB_W/2 - TFT_HOLE_INSET)
        hy = ty + sy*(TFT_PCB_D/2 - TFT_HOLE_INSET)
        h = Part.makeCylinder(TFT_HOLE_R, 8.0)
        h.Placement = FreeCAD.Placement(FreeCAD.Vector(hx, hy, H-8), FreeCAD.Rotation())
        top = top.cut(h)
print("stage: top tft ok V=", round(top.Volume/1000, 1))

# 4-button diamond under right-thumb arc
bx0, by0 = W*0.78, D*0.20
bsp = 12.0
for (bx, by) in [(bx0, by0-bsp), (bx0-bsp, by0), (bx0+bsp, by0), (bx0, by0+bsp)]:
    dj = math.hypot(bx-jx2, by-jy2)
    assert dj > 12.5 + BTN_FOOT/2 + 1.0, "button inside joy2 thumb well"
    clr = Part.makeCylinder(BTN_FOOT/2+0.6, H)
    clr.Placement = FreeCAD.Placement(FreeCAD.Vector(bx, by, H/2), FreeCAD.Rotation())
    thr = Part.makeCylinder(BTN_PLUNGER_R, H+4)
    thr.Placement = FreeCAD.Placement(FreeCAD.Vector(bx, by, H/2), FreeCAD.Rotation())
    top = top.cut(clr.fuse(thr))
print("stage: top buttons ok V=", round(top.Volume/1000, 1))

# LEDs (2x)
for (lx, ly) in [(jx1-13, jy1+9), (jx1+13, jy1+9)]:
    h = Part.makeCylinder(LED_R, H+2)
    h.Placement = FreeCAD.Placement(FreeCAD.Vector(lx, ly, H/2), FreeCAD.Rotation())
    top = top.cut(h)
print("stage: top leds ok V=", round(top.Volume/1000, 1))

# MODE slot
mx, my = W*0.16, D*0.90
top = top.cut(Part.makeBox(22.0, 8.0, 8.0).translated(FreeCAD.Vector(mx-11, my-4, H-8)))
for dx in (-8, 0, 8):
    nub = Part.makeCylinder(1.8, 3.0)
    nub.Placement = FreeCAD.Placement(FreeCAD.Vector(mx+dx, my, H-2), FreeCAD.Rotation())
    top = top.cut(nub)
print("stage: top mode ok V=", round(top.Volume/1000, 1))

# ===== TRAY (open-top floor + walls) =====
# Floor 2.5mm, walls 2.5mm, height 14mm (enough for Uno + standoffs)
TRAY_H = 14.0
# Outer box slightly larger than palm envelope to allow wall thickness
tray_outer = Part.makeBox(W+2*WALL, D+2*WALL, TRAY_H)
tray_outer.translate(FreeCAD.Vector(-WALL, -WALL, 0))
# Inner cavity (open top)
tray_inner = Part.makeBox(W, D, TRAY_H+1)   # +1 to ensure full cut
tray_inner.translate(FreeCAD.Vector(0, 0, 0))
tray = tray_outer.cut(tray_inner)
print("tray outer V=", round(tray_outer.Volume/1000, 1))
print("stage: tray cavity ok V=", round(tray.Volume/1000, 1))

# Arduino Uno on the floor standoffs (6mm tall)
SO_H = 6.0
ux0, uy0 = W/2 - UNO_W/2, D/2 - UNO_D/2  # center Uno on tray floor
for (hx, hy) in UNO_HOLES:
    x, y = ux0 + hx, uy0 + hy
    so = Part.makeCylinder(3.5, SO_H)
    so.Placement = FreeCAD.Placement(FreeCAD.Vector(x, y, 0), FreeCAD.Rotation())
    hole = Part.makeCylinder(M3_R, SO_H+2)
    hole.Placement = FreeCAD.Placement(FreeCAD.Vector(x, y, -1), FreeCAD.Rotation())
    tray = tray.fuse(so.cut(hole))
print("stage: tray standoffs ok V=", round(tray.Volume/1000, 1))

# USB-B + barrel jack cutouts on the -X wall
# Connector centerlines from Uno lower-left corner (ux0,uy0)
pcb_top = SO_H + 1.6
usb = Part.makeBox(WALL+8.0, 14.0, 12.0).translated(
    FreeCAD.Vector(-WALL-4.0, uy0+37.5-7.0, pcb_top))
jack = Part.makeBox(WALL+8.0, 11.0, 12.0).translated(
    FreeCAD.Vector(-WALL-4.0, uy0+8.0-5.5, pcb_top))
tray = tray.cut(usb).cut(jack)
print("stage: tray cutouts ok V=", round(tray.Volume/1000, 1))

# ===== LID SCREW POSTS in the TRAY (4 symmetric corners) =====
POST_INSET = 9.0
POST_R = 4.0
POST_TAP_R = 1.35
POST_TOP = TRAY_H - 5.0  # posts stop 5mm below tray top
LID_SCREW_XY = [(POST_INSET,        POST_INSET),
                (W - POST_INSET,    POST_INSET),
                (W - POST_INSET,    D - POST_INSET),
                (POST_INSET,        D - POST_INSET)]
for (x, y) in LID_SCREW_XY:
    boss = Part.makeCylinder(POST_R, POST_TOP)
    boss.Placement = FreeCAD.Placement(FreeCAD.Vector(x, y, 0), FreeCAD.Rotation())
    pilot = Part.makeCylinder(POST_TAP_R, POST_TOP+2)
    pilot.Placement = FreeCAD.Placement(FreeCAD.Vector(x, y, 2.0), FreeCAD.Rotation())
    tray = tray.fuse(boss).cut(pilot)
print("stage: tray posts ok V=", round(tray.Volume/1000, 1))

tray_obj = doc.addObject("Part::Feature", "Tray")
tray_obj.Shape = tray
top_obj = doc.addObject("Part::Feature", "TopShell")
top_obj.Shape = top

# ===== TOP SHELL COUNTERBORED SCREW HOLES =====
SCREW_CLEAR_R = 1.7
CBORE_R = 3.2
CBORE_DEPTH = 2.5
for (x, y) in LID_SCREW_XY:
    thru = Part.makeCylinder(SCREW_CLEAR_R, 8.0)
    thru.Placement = FreeCAD.Placement(FreeCAD.Vector(x, y, H), FreeCAD.Rotation())
    cbore = Part.makeCylinder(CBORE_R, CBORE_DEPTH)
    cbore.Placement = FreeCAD.Placement(FreeCAD.Vector(x, y, H - CBORE_DEPTH), FreeCAD.Rotation())
    top = top.cut(thru).cut(cbore)
print("stage: top screw holes ok V=", round(top.Volume/1000, 1))

doc.recompute()

# ===== SAVE =====
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CyclUnoCase_v10.FCStd")
doc.saveAs(out)
print("TRAY V=", round(tray.Volume/1000, 1), "cm3  watertight=", tray.isValid())
print("TOP  V=", round(top.Volume/1000, 1), "cm3  valid=", top.isValid())
print("screw holes (centered rect):", LID_SCREW_XY)
print("saved:", out)
