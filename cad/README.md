# CAD — provisional PTK 7465 MG prototype, millimetres

`assembly.step` includes four original printed parts and simplified purchased-part envelopes. Import STEP into Fusion, SolidWorks, FreeCAD or Onshape. The parametric source is `build_cad.py` (CadQuery; generated and checked using 2.8.0). This is newly constructed geometry, not copied from the reference STL files.

The CAD now uses a **PTK 7465-family envelope**, but the only dimensioned illustration located is labeled **7465W MG**; the ordered servo is **7465 MG (non-W)**. The [manufacturer's related MG-D listing](https://www.ptkhobby.com/en/sys-pd/234.html) gives the same 23.9 × 12 × 26.6 mm class and 25T output, while the [dimensioned 7465W illustration](https://manuals.plus/ae/1005008789583991) shows a 23.8 mm body, 12 mm width, 31.8 mm ear span, about 27.8 mm mounting pitch, 22 mm main case depth and 30.1 mm overall height including spline. These are **provisional dimensions**, not a verified drawing of the received non-W units. The horn face, boss and mounting interface still require caliper checks. The generated STEP/STL files are a reviewable starting point, not a print-and-assemble guarantee.

| Print one each | Export | Notes |
|---|---|---|
| Base with integral lower-servo mount | `base.step`, `base.stl` | Flat base down; support the upper mounting crossbar as needed |
| Middle link with perpendicular upper-servo mount | `middle_link.step`, `middle_link.stl` | Orient to strengthen the thin spine and lower bridge; local support may be needed |
| Upper paddle / horn adapter | `paddle.step`, `paddle.stl` | Broad face down; support adapter step if needed |
| Battery guard | `battery_guard.step`, `battery_guard.stl` | Roof face on bed, end feet upward; ties go across roof |

Two disposable test pieces are also generated: `servo_mount_fit_coupon.step/.stl` reproduces the ear frame and body opening, and `horn_fit_coupon.step/.stl` reproduces the adapter face, center access and four radial slots. Print these first after the servos arrive, and fill the [incoming measurement sheet](FIT_CHECK.md). The coupons are **not** installed on the robot.

STLs retain the assembly coordinates. Use the slicer's place-on-bed/orient tools for each part; they are not prearranged on a print plate. Start with a 0.4 mm nozzle, 0.2 mm layers, 4 walls and 30–40% infill in PLA+ or PETG. These are starting settings; thin members become almost solid. Use the actual sliced masses in simulation. CAD solid-volume masses are only upper-bound estimates for a chosen density.

Overall upright size 70 × 64 × 132 mm. Joint origins `(0,0,27)` and `(0,0,72)` mm; axes +X then +Y at neutral. The PTK body opening uses **23.9 × 12.0 mm nominal** plus **0.3 mm per-side clearance**; the provisional flange-hole pitch is **27.8 mm**, and the nominal output-axis offset is **6.0 mm** toward one end of the case. These are parameters in `build_cad.py`, not fixed measured truths. Neither SG90 nor FT90M horns are interchangeable with the likely PTK **25T ~5 mm** spline; use the included PTK OEM horns.

**Fit-check parameters:** `HORN_FACE=16.5 mm` is an assumed external horn face relative to the robot centerline, not a measured dimension. The printed disk has a **6.8 mm center opening** for OEM horn/shaft access and four radial **2.2 mm slots** for a drilled OEM cross/double horn. Use two opposed lateral slots, not the slot under the beam. Fit-check horn thickness, slot-to-horn-hole location, screw length, nut/washer clearance, center-screw access, wire exit and spline engagement on physical hardware. Do not print a replacement spline or force a center screw with an unverified thread.

On receipt, measure and record: case length/width/depth; ear span and hole centers/diameters; output-axis offset from the case center; flange face from the back; boss and shaft projection; OEM horn arm thickness, radius and hole diameter; OEM center-screw thread/length. Adjust the parameters and rerun the generator before final printing. Check both servos: small manufacturing or variant differences matter at a 0.3 mm nominal cavity clearance.

The regenerated **provisional** assembly has no nominal volume intersections in `nominal_clashes.json`. `motion_check.json` checks 25 configurations across ±80 degrees for the principal rigid bodies; it does not check a continuous sweep or the real horns, fasteners, leads, ties or print tolerances. Passing this check is not a guarantee of a usable motion range or physical recovery.

No extra bearing is specified in Rev A. It is compact, but impacts load the small servo output bearings/gears. Inspect backlash and horn loosening during testing. An opposed support bearing would be a later durability upgrade requiring a revised bracket and BOM.

Regenerate with a separate CAD environment:

```sh
python3.12 -m venv .venv-cad
.venv-cad/bin/pip install cadquery==2.8.0 matplotlib
.venv-cad/bin/python cad/build_cad.py
.venv-cad/bin/python cad/check_motion.py
.venv-cad/bin/python cad/render_preview.py
```

Keep the CAD and training environments separate; their NumPy dependency ranges differ.
