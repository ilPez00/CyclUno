import FreeCAD, Part, math

doc = FreeCAD.newDocument("CyclUnoCase_v05")

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
W = PALM_W + 12.0      # 107
D = PALM_L + 6.0       # 111
H = 38.0
WALL = 2.5

# ===== 1. SHELL: rounded box (reliable), safe edge fillet =====
outer = Part.makeBox(W, D, H)
ve = [e for e in outer.Edges if abs(e.BoundBox.ZLength-H)<1e-3 and e.BoundBox.ZLength>10]
base = outer.makeFillet(2.0, ve) if ve else outer
# hollow
cav = Part.makeBox(W-2*WALL, D-2*WALL, H-5.0-WALL)
cav.Placement = FreeCAD.Placement(FreeCAD.Vector(WALL, WALL, WALL), FreeCAD.Rotation())
base = base.cut(cav)
# floor cap
floor = Part.makeBox(W, D, WALL)
base = base.fuse(floor)

# ===== 2. THUMB WELLS (verified sphere.common) =====
def thumb_well(xc, yc, r, depth):
    sph = Part.makeSphere(r).translated(FreeCAD.Vector(xc,yc,H))
    cut = Part.makeBox(2*r, 2*r, depth+2).translated(FreeCAD.Vector(xc-r, yc-r, H-depth))
    return sph.common(cut)

jx1, jy1 = W*0.30, D*0.34
jx2, jy2 = W*0.70, D*0.34
base = base.cut(thumb_well(jx1, jy1, 16.0, 6.0)).cut(thumb_well(jx2, jy2, 16.0, 6.0))

# ===== 3. JOYSTICK: counterbore + chamfer bezel =====
def joy_mount(xc, yc, tilt):
    shaft = Part.makeCylinder(JOY_SHAFT_R+1.0, H+4)
    shaft.Placement = FreeCAD.Placement(FreeCAD.Vector(xc,yc,H/2), FreeCAD.Rotation(0, math.radians(tilt), 0))
    bez = Part.makeCone(JOY_SHAFT_R+1.0, JOY_SHAFT_R+6.0, 3.0)
    bez.Placement = FreeCAD.Placement(FreeCAD.Vector(xc,yc,H-3.0), FreeCAD.Rotation(0, math.radians(tilt), 0))
    return shaft.fuse(bez)

base = base.cut(joy_mount(jx1, jy1, 12.0)).cut(joy_mount(jx2, jy2, -12.0))

# ===== 4. OLED: recessed pocket + glass window =====
ox, oy = W*0.5, D*0.74
pocket = Part.makeBox(OLED_PCB_W+4, OLED_PCB_D+4, 6.0)
pocket.Placement = FreeCAD.Placement(FreeCAD.Vector(ox-OLED_PCB_W/2-2, oy-OLED_PCB_D/2-2, H-6.0), FreeCAD.Rotation())
base = base.cut(pocket)
window = Part.makeBox(OLED_GLASS_W, OLED_GLASS_D, 4.0)
window.Placement = FreeCAD.Placement(FreeCAD.Vector(ox-OLED_GLASS_W/2, oy-OLED_GLASS_D/2, H-4.0), FreeCAD.Rotation())
base = base.cut(window)

# ===== 5. BUTTONS: counterbored holes (diamond around joy2) =====
bsp = 12.0
for (bx,by) in [(jx2, jy2-bsp),(jx2-bsp, jy2),(jx2+bsp, jy2),(jx2, jy2+bsp)]:
    clr = Part.makeCylinder(BTN_FOOT/2+0.6, H)
    clr.Placement = FreeCAD.Placement(FreeCAD.Vector(bx,by,H/2), FreeCAD.Rotation())
    thr = Part.makeCylinder(2.0, H+4)
    thr.Placement = FreeCAD.Placement(FreeCAD.Vector(bx,by,H/2), FreeCAD.Rotation())
    base = base.cut(clr.fuse(thr))

# ===== 6. LEDs =====
for (lx,ly) in [(jx1-11, jy1+7),(jx1+11, jy1+7)]:
    h = Part.makeCylinder(2.6, H+2)
    h.Placement = FreeCAD.Placement(FreeCAD.Vector(lx,ly,H/2), FreeCAD.Rotation())
    base = base.cut(h)

# ===== 7. MODE detent rocker =====
mx, my = W*0.16, D*0.90
slot = Part.makeBox(22.0, 8.0, 8.0)
slot.Placement = FreeCAD.Placement(FreeCAD.Vector(mx-11, my-4, H-8), FreeCAD.Rotation())
base = base.cut(slot)
for dx in [-8,0,8]:
    nub = Part.makeCylinder(1.8, 3.0)
    nub.Placement = FreeCAD.Placement(FreeCAD.Vector(mx+dx, my, H-2), FreeCAD.Rotation())
    base = base.cut(nub)

# ===== 8. UNO standoffs (real hole spacing) =====
ux0 = W*0.5 - UNO_W/2 + 4.0
uy0 = D*0.30
holes_xy = [(ux0, uy0),(ux0+UNO_W-8, uy0),(ux0, uy0+UNO_D-8),(ux0+UNO_W-8, uy0+UNO_D-8)]
so_z0, so_z1 = WALL, H-5.0
so_h = so_z1-so_z0
standoffs=[]
for (x,y) in holes_xy:
    so = Part.makeCylinder(5.0, so_h)
    so.Placement = FreeCAD.Placement(FreeCAD.Vector(x,y,so_z0), FreeCAD.Rotation())
    hole = Part.makeCylinder(UNO_HOLE_R, so_h+2)
    hole.Placement = FreeCAD.Placement(FreeCAD.Vector(x,y,so_z0-1), FreeCAD.Rotation())
    standoffs.append(so.cut(hole))
sc = standoffs[0]
for s in standoffs[1:]: sc = sc.fuse(s)
base = base.fuse(sc)

base_obj = doc.addObject("Part::Feature","Base_v05")
base_obj.Shape = base

# ===== LID =====
lid = Part.makeBox(W, D, 5.0)
lve = [e for e in lid.Edges if abs(e.BoundBox.ZLength-5.0)<1e-3 and e.BoundBox.ZLength>10]
lid = lid.makeFillet(2.0, lve) if lve else lid
for (x,y) in holes_xy:
    h = Part.makeCylinder(M3_R+0.5, 7.0)
    h.Placement = FreeCAD.Placement(FreeCAD.Vector(x,y,-1), FreeCAD.Rotation())
    lid = lid.cut(h)
lid_obj = doc.addObject("Part::Feature","Lid_v05")
lid_obj.Shape = lid

doc.recompute()
print("BASE v05 vol:", round(base.Volume/1000,1),"cm3  z[0,%.0f]"%H)
print("LID  v05 vol:", round(lid.Volume/1000,1),"cm3")
print("joy@(%.0f,%.0f)+(%.0f,%.0f) OLED@(%.0f,%.0f) MODE@(%.0f,%.0f)"%(jx1,jy1,jx2,jy2,ox,oy,mx,my))
print("uno standoffs @", holes_xy)
