import FreeCAD, Part

doc = FreeCAD.newDocument("CyclUnoCase_v02")

W, D, H = 94.0, 66.0, 34.0     # outer
t = 2.0                          # wall
cw, cd, ch = 90.0, 62.0, 30.0   # cavity
lid_t = 4.0                       # lid thickness
inset = 10.0                     # standoff inset from edges
so_r = 4.0                       # standoff outer radius
tap_r = 1.3                      # M3 tap hole radius
clr_r = 1.8                      # lid clearance hole radius

# ---- BASE SHELL ----
outer = Part.makeBox(W, D, H)
cavity = Part.makeBox(cw, cd, ch)
cavity.Placement = FreeCAD.Placement(FreeCAD.Vector((W-cw)/2,(D-cd)/2,t), FreeCAD.Rotation())
base = outer.cut(cavity)

# USB slot on +X end wall
usb = Part.makeBox(12.0, 8.0, 6.0)
usb.Placement = FreeCAD.Placement(FreeCAD.Vector(W-3.0, D/2-4.0, 6.0), FreeCAD.Rotation())
base = base.cut(usb)

# ---- STANDOFFS (floor -> lid seat) ----
so_z0, so_z1 = t, H - lid_t          # 2 -> 30
so_h = so_z1 - so_z0
xs = [inset, W-inset]
ys = [inset, D-inset]
standoffs = []
for x in xs:
    for y in ys:
        so = Part.makeCylinder(so_r, so_h)
        so.Placement = FreeCAD.Placement(FreeCAD.Vector(x,y,so_z0), FreeCAD.Rotation())
        hole = Part.makeCylinder(tap_r, so_h+2)
        hole.Placement = FreeCAD.Placement(FreeCAD.Vector(x,y,so_z0-1), FreeCAD.Rotation())
        so = so.cut(hole)
        standoffs.append(so)
so_comp = standoffs[0]
for s in standoffs[1:]:
    so_comp = so_comp.fuse(s)

base = base.fuse(so_comp)

base_obj = doc.addObject("Part::Feature","Base_v02")
base_obj.Shape = base

# ---- LID (separate part, screw-on) ----
lid = Part.makeBox(W, D, lid_t)
lid.Placement = FreeCAD.Placement(FreeCAD.Vector(0,0,H-lid_t), FreeCAD.Rotation())
for x in xs:
    for y in ys:
        # clearance hole through lid
        h = Part.makeCylinder(clr_r, lid_t+2)
        h.Placement = FreeCAD.Placement(FreeCAD.Vector(x,y,H-lid_t-1), FreeCAD.Rotation())
        lid = lid.cut(h)
        # countersink cone on top
        cs = Part.makeCone(clr_r, clr_r+2.5, 2.0)
        cs.Placement = FreeCAD.Placement(FreeCAD.Vector(x,y,H-1), FreeCAD.Rotation())
        lid = lid.cut(cs)

lid_obj = doc.addObject("Part::Feature","Lid_v02")
lid_obj.Shape = lid

doc.recompute()
print("BASE bounds:", base.BoundBox.XLength, base.BoundBox.YLength, base.BoundBox.ZLength, "vol cm3:", round(base.Volume/1000,1))
print("LID  bounds:", lid.BoundBox.XLength, lid.BoundBox.YLength, lid.BoundBox.ZLength, "vol cm3:", round(lid.Volume/1000,1))
print("Standoff centers:", [(x,y) for x in xs for y in ys])
