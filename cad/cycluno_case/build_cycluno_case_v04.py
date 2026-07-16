import FreeCAD, Part, math

# ===== HAND ENVELOPE (parameterize -> swap YOUR real measures) =====
PALM_W = 95.0     # mm across knuckles
PALM_L = 105.0    # mm wrist crease -> finger base
W = PALM_W + 10.0   # 105
D = PALM_L + 4.0     # 109
H = 36.0
t = 2.5
lid_t = 5.0
inset = 12.0
so_r = 4.5
tap_r = 1.3

# ---- BASE shell via rounded box (R < wall so it stays a shell) ----
R = 2.0   # safe: < wall thickness t=2.5
outer = Part.makeBox(W, D, H)
# safe fillet R=2.0 < wall t=2.5
_ve=[e for e in outer.Edges if abs(e.BoundBox.ZLength-H)<1e-3 and e.BoundBox.ZLength>10]
outer = outer.makeFillet(2.0, _ve) if _ve else outer
cavity = Part.makeBox(W-2*t, D-2*t, H-lid_t-t)
cavity.Placement = FreeCAD.Placement(FreeCAD.Vector(t, t, t), FreeCAD.Rotation())
base = outer.cut(cavity)

# USB slot on +X (wrist-side) end
usb = Part.makeBox(13.0, 9.0, 7.0)
usb.Placement = FreeCAD.Placement(FreeCAD.Vector(W-3.0, D/2-4.5, 7.0), FreeCAD.Rotation())
base = base.cut(usb)

# ===== DERIVED LAYOUT (from hand, not rectangle) =====
# Thumbs rest near WRIST side (y small). Sticks LOW.
jx1, jy1 = W*0.30, D*0.34
jx2, jy2 = W*0.70, D*0.34
def stick_bore(xc, yc, r, tilt, sign):
    h = Part.makeCylinder(r, 16.0)
    h.Placement = FreeCAD.Placement(FreeCAD.Vector(xc, yc, H-11.0),
                                FreeCAD.Rotation(0, math.radians(tilt*sign), 0))
    return h
base = base.cut(stick_bore(jx1, jy1, 5.5, 15.0, +1))
base = base.cut(stick_bore(jx2, jy2, 5.5, 15.0, -1))

# OLED = UPPER sight-line (eyes look at top, away from wrists)
ox, oy = W*0.5, D*0.74
oled = Part.makeBox(32.0, 32.0, 7.0)
oled.Placement = FreeCAD.Placement(FreeCAD.Vector(ox-16.0, oy-16.0, H-6.0), FreeCAD.Rotation())
base = base.cut(oled)

# BUTTONS = diamond in RIGHT-thumb arc around joy2
bsp = 11.0
for (bx,by,name) in [(jx2, jy2-bsp,'A'),(jx2-bsp, jy2,'B'),
                        (jx2+bsp, jy2,'X'),(jx2, jy2+bsp,'Y')]:
    h = Part.makeCylinder(3.6, 7.0)
    h.Placement = FreeCAD.Placement(FreeCAD.Vector(bx,by,H-6.0), FreeCAD.Rotation())
    base = base.cut(h)

# LEDS = left-thumb arc (REC/LINK), near joy1
for (lx,ly) in [(jx1-10, jy1+6),(jx1+10, jy1+6)]:
    h = Part.makeCylinder(2.6, 7.0)
    h.Placement = FreeCAD.Placement(FreeCAD.Vector(lx,ly,H-6.0), FreeCAD.Rotation())
    base = base.cut(h)

# MODE = detent rocker, INDEX side (top-LEFT edge)
mx, my = W*0.16, D*0.88
mode = Part.makeBox(20.0, 7.0, 7.0)
mode.Placement = FreeCAD.Placement(FreeCAD.Vector(mx-10.0, my-3.5, H-6.0), FreeCAD.Rotation())
base = base.cut(mode)
for dx in [-7.0, 0.0, 7.0]:
    nub = Part.makeCylinder(1.6, 3.0)
    nub.Placement = FreeCAD.Placement(FreeCAD.Vector(mx+dx, my, H-2.0), FreeCAD.Rotation())
    base = base.cut(nub)

# ---- STANDOFFS ----
xs = [inset, W-inset]; ys = [inset, D-inset]
so_z0, so_z1 = t, H-lid_t
so_h = so_z1-so_z0
standoffs=[]
for x in xs:
    for y in ys:
        so = Part.makeCylinder(so_r, so_h)
        so.Placement = FreeCAD.Placement(FreeCAD.Vector(x,y,so_z0), FreeCAD.Rotation())
        hole = Part.makeCylinder(tap_r, so_h+2)
        hole.Placement = FreeCAD.Placement(FreeCAD.Vector(x,y,so_z0-1), FreeCAD.Rotation())
        standoffs.append(so.cut(hole))
sc = standoffs[0]
for s in standoffs[1:]: sc = sc.fuse(s)
base = base.fuse(sc)

doc = FreeCAD.ActiveDocument if FreeCAD.ActiveDocument else FreeCAD.newDocument("CyclUnoCase_v04")
base_obj = doc.addObject("Part::Feature","Base_v04")
base_obj.Shape = base

lid = Part.makeBox(W, D, lid_t)
_lve=[e for e in lid.Edges if abs(e.BoundBox.ZLength-lid_t)<1e-3 and e.BoundBox.ZLength>10]
lid = lid.makeFillet(2.0, _lve) if _lve else lid
lid.Placement = FreeCAD.Placement(FreeCAD.Vector(0,0,H-lid_t), FreeCAD.Rotation())
for x in xs:
    for y in ys:
        h = Part.makeCylinder(1.9, lid_t+2)
        h.Placement = FreeCAD.Placement(FreeCAD.Vector(x,y,H-lid_t-1), FreeCAD.Rotation())
        lid = lid.cut(h)
lid_obj = doc.addObject("Part::Feature","Lid_v04")
lid_obj.Shape = lid

doc.recompute()
print("PALM envelope: W=%.0f D=%.0f (palm %.0fx%.0f)"%(W,D,PALM_W,PALM_L))
print("joy1=(%.0f,%.0f) joy2=(%.0f,%.0f) OLED=(%.0f,%.0f) MODE=(%.0f,%.0f)"%(jx1,jy1,jx2,jy2,ox,oy,mx,my))
print("BASE vol=%.1fcm3 (shell, expect ~115)  LID vol=%.1fcm3"%(base.Volume/1000, lid.Volume/1000))
