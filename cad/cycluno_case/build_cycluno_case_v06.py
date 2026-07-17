import FreeCAD, Part, math

doc = FreeCAD.newDocument("CyclUnoCase_v06")

# ===== REAL COMPONENT DIMS (research) =====
JOY_SHAFT_R = 5.5
OLED_PCB_W, OLED_PCB_D = 30.0, 40.0
OLED_GLASS_W, OLED_GLASS_D = 20.0, 33.0
BTN_FOOT = 6.0
UNO_W, UNO_D = 68.6, 53.4
UNO_HOLE_R = 1.6
M3_R = 1.3

# ===== PALM ENVELOPE (avg hand; parameterize) =====
PALM_W, PALM_L = 95.0, 105.0
W, D, H = PALM_W+12.0, PALM_L+6.0, 38.0   # 107 x 111 x 38
WALL = 2.5

# ===== loft CONTOUR (solid) -- proven reliable =====
def profile(w, d, c):
    pts = [FreeCAD.Vector(-w+c,-d), FreeCAD.Vector(w-c,-d), FreeCAD.Vector(w,-d+c),
            FreeCAD.Vector(w,d-c), FreeCAD.Vector(w-c,d), FreeCAD.Vector(-w+c,d),
            FreeCAD.Vector(-w,d-c), FreeCAD.Vector(-w,-d+c), FreeCAD.Vector(-w+c,-d)]
    return Part.makePolygon(pts)
def atZ(wire, z): return Part.Face(wire).translated(FreeCAD.Vector(0,0,z))

SEC = [(W/2*0.82, D/2*0.80, 8.0, 0.0),
       (W/2,      D/2,     12.0, H*0.45),
       (W/2*0.88, D/2*0.86, 8.0, H)]
outer = Part.makeLoft([atZ(profile(s[0],s[1],s[2]), s[3]) for s in SEC])
print("loft solid V=", round(outer.Volume/1000,1))

# ===== hollow via makeOffsetShape (reliable, not boolean-on-lofts) =====
shell = outer.makeOffsetShape(-WALL, 1e-4, True, False, 0)
if shell.isNull():
    shell = outer.makeOffsetShape(-WALL, 1e-4, False, False, 0)
print("shell V=", round(shell.Volume/1000,1))
base = shell
# floor cap (close bottom -> pocket)
bot = Part.makeBox(W, D, WALL)
base = base.fuse(bot)

# ===== THUMB WELLS (sphere.common, verified) =====
def thumb_well(xc, yc, r, depth):
    sph = Part.makeSphere(r).translated(FreeCAD.Vector(xc,yc,H))
    cut = Part.makeBox(2*r, 2*r, depth+2).translated(FreeCAD.Vector(xc-r, yc-r, H-depth))
    return sph.common(cut)
jx1, jy1 = W*0.30, D*0.34
jx2, jy2 = W*0.70, D*0.34
base = base.cut(thumb_well(jx1, jy1, 16.0, 6.0)).cut(thumb_well(jx2, jy2, 16.0, 6.0))

# ===== JOYSTICK: counterbore + chamfer bezel =====
def joy_mount(xc, yc, tilt):
    shaft = Part.makeCylinder(JOY_SHAFT_R+1.0, H+4)
    shaft.Placement = FreeCAD.Placement(FreeCAD.Vector(xc,yc,H/2), FreeCAD.Rotation(0, math.radians(tilt), 0))
    bez = Part.makeCone(JOY_SHAFT_R+1.0, JOY_SHAFT_R+6.0, 3.0)
    bez.Placement = FreeCAD.Placement(FreeCAD.Vector(xc,yc,H-3.0), FreeCAD.Rotation(0, math.radians(tilt), 0))
    return shaft.fuse(bez)
base = base.cut(joy_mount(jx1, jy1, 12.0)).cut(joy_mount(jx2, jy2, -12.0))

# ===== OLED: recessed pocket + glass window =====
ox, oy = W*0.5, D*0.74
base = base.cut(Part.makeBox(OLED_PCB_W+4, OLED_PCB_D+4, 6.0).translated(FreeCAD.Vector(ox-OLED_PCB_W/2-2, oy-OLED_PCB_D/2-2, H-6.0)))
base = base.cut(Part.makeBox(OLED_GLASS_W, OLED_GLASS_D, 4.0).translated(FreeCAD.Vector(ox-OLED_GLASS_W/2, oy-OLED_GLASS_D/2, H-4.0)))

# ===== BUTTONS: counterbored (diamond around joy2) =====
bsp = 12.0
for (bx,by) in [(jx2, jy2-bsp),(jx2-bsp, jy2),(jx2+bsp, jy2),(jx2, jy2+bsp)]:
    clr = Part.makeCylinder(BTN_FOOT/2+0.6, H)
    clr.Placement = FreeCAD.Placement(FreeCAD.Vector(bx,by,H/2), FreeCAD.Rotation())
    thr = Part.makeCylinder(2.0, H+4)
    thr.Placement = FreeCAD.Placement(FreeCAD.Vector(bx,by,H/2), FreeCAD.Rotation())
    base = base.cut(clr.fuse(thr))

# ===== LEDs =====
for (lx,ly) in [(jx1-11, jy1+7),(jx1+11, jy1+7)]:
    h = Part.makeCylinder(2.6, H+2)
    h.Placement = FreeCAD.Placement(FreeCAD.Vector(lx,ly,H/2), FreeCAD.Rotation())
    base = base.cut(h)

# ===== MODE detent rocker =====
mx, my = W*0.16, D*0.90
base = base.cut(Part.makeBox(22.0, 8.0, 8.0).translated(FreeCAD.Vector(mx-11, my-4, H-8)))
for dx in [-8,0,8]:
    nub = Part.makeCylinder(1.8, 3.0)
    nub.Placement = FreeCAD.Placement(FreeCAD.Vector(mx+dx, my, H-2), FreeCAD.Rotation())
    base = base.cut(nub)

# ===== UNO standoffs (real hole spacing) =====
ux0, uy0 = W*0.5 - UNO_W/2 + 4.0, D*0.30
holes_xy = [(ux0, uy0),(ux0+UNO_W-8, uy0),(ux0, uy0+UNO_D-8),(ux0+UNO_W-8, uy0+UNO_D-8)]
so_z0, so_z1 = WALL, H-5.0
for (x,y) in holes_xy:
    so = Part.makeCylinder(5.0, so_z1-so_z0)
    so.Placement = FreeCAD.Placement(FreeCAD.Vector(x,y,so_z0), FreeCAD.Rotation())
    hole = Part.makeCylinder(UNO_HOLE_R, so_z1-so_z0+2)
    hole.Placement = FreeCAD.Placement(FreeCAD.Vector(x,y,so_z0-1), FreeCAD.Rotation())
    base = base.fuse(so.cut(hole))

base_obj = doc.addObject("Part::Feature","Base_v06")
base_obj.Shape = base

# ===== LID (lofted top, matching contour) =====
lf = [atZ(profile(s[0],s[1],s[2]), min(s[3], 5.0)) for s in SEC]
lid = Part.makeLoft(lf)
for (x,y) in holes_xy:
    h = Part.makeCylinder(M3_R+0.5, 7.0)
    h.Placement = FreeCAD.Placement(FreeCAD.Vector(x,y,-1), FreeCAD.Rotation())
    lid = lid.cut(h)
lid_obj = doc.addObject("Part::Feature","Lid_v06")
lid_obj.Shape = lid

doc.recompute()
print("BASE v06 V=", round(base.Volume/1000,1), "cm3  z[0,%.0f]"%H)
print("LID  v06 V=", round(lid.Volume/1000,1), "cm3")
print("joy@(%.0f,%.0f)+(%.0f,%.0f) OLED@(%.0f,%.0f) MODE@(%.0f,%.0f)"%(jx1,jy1,jx2,jy2,ox,oy,mx,my))
print("uno standoffs @", holes_xy)
