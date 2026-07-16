import FreeCAD, Part, math

doc = FreeCAD.newDocument("CyclUnoCase_v03")

W, D, H = 96.0, 68.0, 34.0     # outer (slightly larger for rake)
t = 2.0
cw, cd, ch = 90.0, 62.0, 30.0
lid_t = 4.0
inset = 10.0
so_r = 4.0
tap_r = 1.3

# ---- BASE (rounded grip: fillet the 4 vertical edges) ----
outer = Part.makeBox(W, D, H)
# round the 4 long edges via fillet on the solid
outer = outer.makeFillet(8.0, outer.Edges) if False else outer  # defer; use chamfer-free fillet after shell
cavity = Part.makeBox(cw, cd, ch)
cavity.Placement = FreeCAD.Placement(FreeCAD.Vector((W-cw)/2,(D-cd)/2,t), FreeCAD.Rotation())
base = outer.cut(cavity)

# USB slot on +X end
usb = Part.makeBox(12.0, 8.0, 6.0)
usb.Placement = FreeCAD.Placement(FreeCAD.Vector(W-3.0, D/2-4.0, 6.0), FreeCAD.Rotation())
base = base.cut(usb)

# ---- RAKED STICK CUTOUTS (tilt the bore axis, not just move) ----
# joy1 lower-left, rake ~20deg toward center; joy2 upper-right
def raked_bore(xc, yc, r, tilt_deg, axis='x'):
    h = Part.makeCylinder(r, 14.0)
    # tilt around the perpendicular horizontal axis
    if axis == 'x':
        rot = FreeCAD.Rotation(math.radians(tilt_deg),0,0)
    else:
        rot = FreeCAD.Rotation(0,math.radians(tilt_deg),0)
    h.Placement = FreeCAD.Placement(FreeCAD.Vector(xc,yc,H-10.0), rot)
    return h

# joy1 (left hand) lower-left, tilt +x (toward right/center)
base = base.cut(raked_bore(30.0, 18.0, 5.0, 18.0, 'y'))
# joy2 (right hand) upper-right, tilt -x
base = base.cut(raked_bore(66.0, 50.0, 5.0, -18.0, 'y'))

# ---- MODE ROCKER SLOT (top edge, center-right) ----
# rectangular slot 18x6 through top, for 3-pos slide switch
mode_slot = Part.makeBox(18.0, 6.0, 6.0)
mode_slot.Placement = FreeCAD.Placement(FreeCAD.Vector(W/2-9.0, D-6.0, H-6.0), FreeCAD.Rotation())
base = base.cut(mode_slot)

# ---- OLED window (top-center, status compass) ----
oled = Part.makeBox(30.0, 30.0, 6.0)
oled.Placement = FreeCAD.Placement(FreeCAD.Vector(W/2-15.0, D/2-15.0, H-6.0), FreeCAD.Rotation())
base = base.cut(oled)

# ---- 4 BUTTONS (diamond under right-thumb arc) ----
# A bottom, B left, X right, Y top around joy2
for (bx,by) in [(66,40),(58,50),(74,50),(66,60)]:
    h = Part.makeCylinder(3.5, 6.0)
    h.Placement = FreeCAD.Placement(FreeCAD.Vector(bx,by,H-6.0), FreeCAD.Rotation())
    base = base.cut(h)

# ---- 2 LEDS ----
for (lx,ly) in [(48,52),(48,44)]:
    h = Part.makeCylinder(2.5, 6.0)
    h.Placement = FreeCAD.Placement(FreeCAD.Vector(lx,ly,H-6.0), FreeCAD.Rotation())
    base = base.cut(h)

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

# ---- ROUND GRIP (fillet the 4 vertical base edges) ----
try:
    edges = [e for e in base.Edges if abs(e.BoundBox.ZLength- (H))<1e-3 and e.BoundBox.ZLength>10]
    base = base.makeFillet(6.0, edges) if edges else base
except Exception as e:
    print("fillet skip:", e)

base_obj = doc.addObject("Part::Feature","Base_v03")
base_obj.Shape = base

# ---- LID ----
lid = Part.makeBox(W, D, lid_t)
lid.Placement = FreeCAD.Placement(FreeCAD.Vector(0,0,H-lid_t), FreeCAD.Rotation())
for x in xs:
    for y in ys:
        h = Part.makeCylinder(1.8, lid_t+2)
        h.Placement = FreeCAD.Placement(FreeCAD.Vector(x,y,H-lid_t-1), FreeCAD.Rotation())
        lid = lid.cut(h)
lid_obj = doc.addObject("Part::Feature","Lid_v03")
lid_obj.Shape = lid

doc.recompute()
print("BASE:", round(base.Volume/1000,1),"cm3  z[0,%.0f]"%H)
print("LID :", round(lid.Volume/1000,1),"cm3")
print("raked sticks @(30,18)+(66,50); MODE slot top-edge; OLED center; 4-btn diamond")
