# CAD — prototype, millimetres

`assembly.step` includes four original printed parts and simplified purchased-part envelopes. Import STEP into Fusion, SolidWorks, FreeCAD or Onshape. The parametric source is `build_cad.py` (CadQuery; generated and checked using 2.8.0). This is newly constructed geometry, not copied from the reference STL files.

| Print one each | Export | Notes |
|---|---|---|
| Base with integral lower-servo mount | `base.step`, `base.stl` | Flat base down; support the upper mounting crossbar as needed |
| Middle link with perpendicular upper-servo mount | `middle_link.step`, `middle_link.stl` | Orient to strengthen the thin spine and lower bridge; local support may be needed |
| Upper paddle / horn adapter | `paddle.step`, `paddle.stl` | Broad face down; support adapter step if needed |
| Battery guard | `battery_guard.step`, `battery_guard.stl` | Roof face on bed, end feet upward; ties go across roof |

STLs retain the assembly coordinates. Use the slicer's place-on-bed/orient tools for each part; they are not prearranged on a print plate. Start with a 0.4 mm nozzle, 0.2 mm layers, 4 walls and 30–40% infill in PLA+ or PETG. These are starting settings; thin members become almost solid. Use the actual sliced masses in simulation. CAD solid-volume masses are only upper-bound estimates for a chosen density.

Overall upright size 70 × 64 × 132 mm. Joint origins `(0,0,27)` and `(0,0,72)` mm; axes +X then +Y at neutral. Body pocket dimensions derive from the FT90M drawing and include 0.3 mm clearance per side. Mount-hole nominal pitch is 28.5 mm, with output axis offset from case center; do not substitute a generic SG90 drawing.

**Fit-check parameters:** `HORN_FACE=13.8 mm` is an assumed external horn face relative to the robot centerline, not a measured dimension. Adapter slots accept a drilled OEM horn. Use two opposed lateral slots, not the slot under the beam. Fit-check screw length, nut/washer clearance, center-screw access, wire exit and spline engagement on physical hardware. Do not print a replacement spline.

The simplified horn envelopes intentionally intersect their servo spline envelopes. Those are the only intended upright overlap entries. `nominal_clashes.json` records all nominal intersections. `motion_check.json` checks 25 configurations across ±80 degrees for the principal rigid bodies; it does not check a continuous sweep or actual fasteners, horns, leads, ties, capacitor or the user's print tolerances. Passing this check is not a guarantee of a usable motion range or physical recovery.

No extra bearing is specified in Rev A. It is compact, but impacts load the small servo output bearings/gears. Inspect backlash and horn loosening during testing. An opposed support bearing would be a later durability upgrade requiring a revised bracket and BOM.

Regenerate with a separate CAD environment:

```sh
python -m venv .venv-cad
.venv-cad/bin/pip install cadquery==2.8.0 matplotlib
.venv-cad/bin/python cad/build_cad.py
.venv-cad/bin/python cad/check_motion.py
.venv-cad/bin/python cad/render_preview.py
```

Keep the CAD and training environments separate; their NumPy dependency ranges differ.
