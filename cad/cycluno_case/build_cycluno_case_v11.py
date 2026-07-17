import FreeCAD, Part, math, os

# ============================================================================
# CyclUnoCase v11 — v10 split (Tray + TopShell) with research-verified dims
# (docs/reference/palm-deck-research.md):
#   * TFT pocket for the real MSP1443 footprint 29.7 x 43.36 mm (VERIFIED),
#     mounted LANDSCAPE (long edge along X) so the pocket stays inside the
#     shell's top face; window = active area 26.2 x 27.2 + 0.5 mm/side.
#     Corner-post pattern is NOT documented by the vendor — posts stay
#     placeholder, MEASURE the real module.
#   * MODE = MTS-103 ON-OFF-ON toggle (AION/OFF/APP): M6 bushing hole
#     (6.2 mm) + 2.4 mm anti-rotation keyway at 6.4 mm offset + body cavity,
#     replacing the generic 22x8 slot. Solder-lug part — flying leads.
#   * Hole sizing per FDM practice: self-tap = nominal -0.25 mm dia,
#     clearance = nominal +0.25 mm dia; bosses widened toward the
#     1x-hole-dia wall rule.
# KNOWN OPEN ISSUE (inherited from v10, left for the CAD line owner): the
# tray outer box (W+2*WALL x D+2*WALL) is wider than the shell footprint at
# z=0 (SEC[0] is ~0.82W x 0.80D), so the two halves do not mate yet.
# ============================================================================

doc = FreeCAD.newDocument("CyclUnoCase_v11")

# ===== REAL COMPONENT DIMS =====
JOY_SHAFT_R = 5.5            # HW-504 shaft clearance radius (hole = R+1)
# MSP1443 (lcdwiki, VERIFIED): PCB 29.7 x 43.36, active 26.2 x 27.2.
# Landscape mount: PCB long edge (43.36, header end) along X.
TFT_PCB_X, TFT_PCB_Y = 43.36, 29.7
TFT_ACT_X, TFT_ACT_Y = 27.2, 26.2    # panel h x w land along X x Y when rotated
TFT_WIN_X = TFT_ACT_X + 1.0          # +0.5 mm clearance per side
TFT_WIN_Y = TFT_ACT_Y + 1.0
TFT_POST_R = 1.15                    # M2.5 self-tap (2.25 dia); MEASURE pattern
TFT_POST_INSET = 2.5
BTN_FOOT = 7.2                       # measured tact switch body width
BTN_PLUNGER_R = 2.0                  # cap stem clearance
LED_DIA = 5.4                        # measured LED body diameter
LED_R = LED_DIA/2 + 0.1              # print clearance -> 2.8
UNO_W, UNO_D = 68.6, 53.4            # datasheet board outline
UNO_HOLES = [(13.97, 2.54), (66.04, 7.62), (66.04, 35.56), (15.24, 50.80)]
UNO_TAP_R = 1.375                    # M3 self-tap into standoff (2.75 dia)
# MTS-103 (handsontec): M6x0.75 bushing, 2.4 mm keyway at 6.4 mm offset,
# body ~13.2 x 7.9 x 9.5 under the bushing.
MTS_HOLE_R = 3.1                     # 6.2 mm panel hole
MTS_KEY_R = 1.2
MTS_KEY_OFF = 6.4
MTS_BODY_X, MTS_BODY_Y, MTS_BODY_Z = 14.2, 8.9, 10.0   # body + 0.5 clearance

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

# ===== TOP SHELL =====
top = Part.makeLoft([atZ(profile(s[0], s[1], s[2]), s[3]) for s in SEC], True)
top.translate(FreeCAD.Vector(W/2, D/2, 0))
print("top shell V=", round(top.Volume/1000, 1))

# Thumb wells
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

# TFT pocket (landscape MSP1443) + active-area window + placeholder posts
tx, ty = W*0.5, D*0.75
POCKET_D = 6.0
pkx, pky = TFT_PCB_X + 1.0, TFT_PCB_Y + 1.0   # +0.5 mm clearance per side
top = top.cut(Part.makeBox(pkx, pky, POCKET_D)
              .translated(FreeCAD.Vector(tx-pkx/2, ty-pky/2, H-POCKET_D)))
top = top.cut(Part.makeBox(TFT_WIN_X, TFT_WIN_Y, POCKET_D)
              .translated(FreeCAD.Vector(tx-TFT_WIN_X/2, ty-TFT_WIN_Y/2, H-POCKET_D-4.0)))
for sx in (-1, 1):
    for sy in (-1, 1):
        hx = tx + sx*(TFT_PCB_X/2 - TFT_POST_INSET)
        hy = ty + sy*(TFT_PCB_Y/2 - TFT_POST_INSET)
        h = Part.makeCylinder(TFT_POST_R, 8.0)
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

# MODE = MTS-103 toggle: M6 bushing hole + keyway + body cavity from below.
# Keyway sits toward -X (inboard) so the lever throw runs along Y.
mx, my = W*0.16, D*0.90
hole = Part.makeCylinder(MTS_HOLE_R, H+2)
hole.Placement = FreeCAD.Placement(FreeCAD.Vector(mx, my, H/2), FreeCAD.Rotation())
key = Part.makeCylinder(MTS_KEY_R, H+2)
key.Placement = FreeCAD.Placement(FreeCAD.Vector(mx - MTS_KEY_OFF, my, H/2), FreeCAD.Rotation())
body = Part.makeBox(MTS_BODY_X, MTS_BODY_Y, MTS_BODY_Z).translated(
    FreeCAD.Vector(mx - MTS_BODY_X/2, my - MTS_BODY_Y/2, H - WALL - MTS_BODY_Z))
top = top.cut(hole).cut(key).cut(body)
print("stage: top mode ok V=", round(top.Volume/1000, 1))

# ===== TRAY (open-top floor + walls) =====
TRAY_H = 14.0
tray_outer = Part.makeBox(W+2*WALL, D+2*WALL, TRAY_H)
tray_outer.translate(FreeCAD.Vector(-WALL, -WALL, 0))
tray_inner = Part.makeBox(W, D, TRAY_H+1)
tray = tray_outer.cut(tray_inner)
print("stage: tray cavity ok V=", round(tray.Volume/1000, 1))

# Arduino Uno floor standoffs: M3 self-tap holes, boss wall toward 1x dia
SO_H = 6.0
SO_R = 4.4
ux0, uy0 = W/2 - UNO_W/2, D/2 - UNO_D/2
for (hx, hy) in UNO_HOLES:
    x, y = ux0 + hx, uy0 + hy
    so = Part.makeCylinder(SO_R, SO_H)
    so.Placement = FreeCAD.Placement(FreeCAD.Vector(x, y, 0), FreeCAD.Rotation())
    hole = Part.makeCylinder(UNO_TAP_R, SO_H+2)
    hole.Placement = FreeCAD.Placement(FreeCAD.Vector(x, y, -1), FreeCAD.Rotation())
    tray = tray.fuse(so.cut(hole))
print("stage: tray standoffs ok V=", round(tray.Volume/1000, 1))

# USB-B + barrel jack cutouts on the -X wall (VERIFY against real board)
pcb_top = SO_H + 1.6
usb = Part.makeBox(WALL+8.0, 14.0, 12.0).translated(
    FreeCAD.Vector(-WALL-4.0, uy0+37.5-7.0, pcb_top))
jack = Part.makeBox(WALL+8.0, 11.0, 12.0).translated(
    FreeCAD.Vector(-WALL-4.0, uy0+8.0-5.5, pcb_top))
tray = tray.cut(usb).cut(jack)
print("stage: tray cutouts ok V=", round(tray.Volume/1000, 1))

# ===== LID SCREW POSTS in the TRAY =====
POST_INSET = 9.0
POST_R = 4.4                 # boss wall toward 1x-hole-dia rule
POST_TAP_R = 1.375           # M3 self-tap (2.75 dia)
POST_TOP = TRAY_H - 5.0
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

# ===== TOP SHELL COUNTERBORED SCREW HOLES =====
SCREW_CLEAR_R = 1.625        # M3 clearance (3.25 dia)
CBORE_R = 3.2
CBORE_DEPTH = 2.5
for (x, y) in LID_SCREW_XY:
    thru = Part.makeCylinder(SCREW_CLEAR_R, 8.0)
    thru.Placement = FreeCAD.Placement(FreeCAD.Vector(x, y, H), FreeCAD.Rotation())
    cbore = Part.makeCylinder(CBORE_R, CBORE_DEPTH)
    cbore.Placement = FreeCAD.Placement(FreeCAD.Vector(x, y, H - CBORE_DEPTH), FreeCAD.Rotation())
    top = top.cut(thru).cut(cbore)
print("stage: top screw holes ok V=", round(top.Volume/1000, 1))

tray_obj = doc.addObject("Part::Feature", "Tray")
tray_obj.Shape = tray
top_obj = doc.addObject("Part::Feature", "TopShell")
top_obj.Shape = top
doc.recompute()

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "CyclUnoCase_v11.FCStd")
doc.saveAs(out)
print("TRAY V=", round(tray.Volume/1000, 1), "cm3  valid=", tray.isValid())
print("TOP  V=", round(top.Volume/1000, 1), "cm3  valid=", top.isValid())
print("TFT landscape pocket @(%.1f,%.1f) %sx%s  MODE MTS-103 @(%.1f,%.1f)"
      % (tx, ty, pkx, pky, mx, my))
print("saved:", out)
