# CAD — provisional PTK 7465 MG prototype, millimetres

`assembly.step` includes four original printed parts and simplified purchased-part envelopes. Import STEP into Fusion, SolidWorks, FreeCAD or Onshape. The parametric source is `build_cad.py` (CadQuery; generated and checked using 2.8.0). This is newly constructed geometry, not copied from the reference STL files. Rev B adds an outboard passive pivot at each hinge, opposite the servo horn.

The CAD now uses a **PTK 7465-family envelope**, but the only dimensioned illustration located is labeled **7465W MG**; the ordered servo is **7465 MG (non-W)**. The [manufacturer's related MG-D listing](https://www.ptkhobby.com/en/sys-pd/234.html) gives the same 23.9 × 12 × 26.6 mm class and 25T output, while the [dimensioned 7465W illustration](https://manuals.plus/ae/1005008789583991) shows a 23.8 mm body, 12 mm width, 31.8 mm ear span, about 27.8 mm mounting pitch, 22 mm main case depth and 30.1 mm overall height including spline. These are **provisional dimensions**, not a verified drawing of the received non-W units. The horn face, boss and mounting interface still require caliper checks. The generated STEP/STL files are a reviewable starting point, not a print-and-assemble guarantee.

| Print one each | Export | Notes |
|---|---|---|
| Base with lower-servo mount and outboard bearing post | `base.step`, `base.stl` | Flat base down; support the mounting crossbar and ream the bearing seat only after a coupon test |
| Middle link with perpendicular upper-servo mount, lower journal and upper outboard support | `middle_link.step`, `middle_link.stl` | Orient to strengthen the thin spine and upper support bridge; local support may be needed |
| Upper paddle / horn adapter with outboard journal | `paddle.step`, `paddle.stl` | Broad face down; support adapter step if needed |
| Battery guard | `battery_guard.step`, `battery_guard.stl` | Roof face on bed, end feet upward; ties go across roof |

Three disposable test pieces are generated: `servo_mount_fit_coupon.step/.stl` reproduces the ear frame and body opening; `horn_fit_coupon.step/.stl` reproduces the adapter face, center access and four radial slots; `pivot_fit_coupon.step/.stl` contains a bearing seat and a separate blind pin bore. Print these first after the servos and proposed pivot hardware arrive, and fill the [incoming measurement sheet](FIT_CHECK.md). The coupons are **not** installed on the robot.

STLs retain the assembly coordinates. Use the slicer's place-on-bed/orient tools for each part; they are not prearranged on a print plate. Start with a 0.4 mm nozzle, 0.2 mm layers, 4 walls and 30–40% infill in PLA+ or PETG. These are starting settings; thin members become almost solid. Use the actual sliced masses in simulation. CAD solid-volume masses are only upper-bound estimates for a chosen density.

Overall upright size 70 × 64 × 132 mm. Joint origins `(0,0,27)` and `(0,0,72)` mm; axes +X then +Y at neutral. The PTK body opening uses **23.9 × 12.0 mm nominal** plus **0.3 mm per-side clearance**; the provisional flange-hole pitch is **27.8 mm**, and the nominal output-axis offset is **6.0 mm** toward one end of the case. These are parameters in `build_cad.py`, not fixed measured truths. Neither SG90 nor FT90M horns are interchangeable with the likely PTK **25T ~5 mm** spline; use the included PTK OEM horns.

**Fit-check parameters:** `HORN_FACE=16.5 mm` is an assumed external horn face relative to the robot centerline, not a measured dimension. The printed disk has a **6.8 mm center opening** for OEM horn/shaft access and four radial **2.2 mm slots** for a drilled OEM cross/double horn. Use two opposed lateral slots, not the slot under the beam. Each disk now has a 12 mm diameter outer hub with a blind 3.05 mm nominal bore for a 3 × 12 mm pin. The fixed bracket has a nominal 8.05 mm bearing pocket, 3 mm deep, with a 6.2 mm rear relief so the shoulder clears the rotating inner race and seats near the outer race. Fit-check horn thickness, slot-to-horn-hole location, screw length, nut/washer clearance, center-screw access, wire exit and spline engagement on physical hardware. Do not print a replacement spline or force a center screw with an unverified thread.

The support is **coaxial** with each servo output: the lower bearing post is part of the base and its pin is in the middle link; the upper bearing block is part of the middle link and its pin is in the paddle. The pin rotates with its link while the bearing outer ring stays with the parent. This creates a second radial support point across the joint, relieving bending at the servo spline and horn. It is a supported shaft, not a literal double-shear fastener. The upper block is reached by a low side bridge, outside the nominal rotating paddle envelope. The brackets and hubs add material and may alter righting dynamics; use sliced masses in the simulator.

**Assembly order:** install each OEM horn and its center screw on the servo first. The printed outer hub blocks straight-on screwdriver access after assembly, so attach the printed adapter to the horn with its two lateral screws afterward. Seat the bearing by pressing only on its outer ring; if the pocket is loose, retain the **outer ring only** with a small amount of suitable adhesive. Trial-fit the pin to the bearing, then retain the pin in the printed blind hub with a controlled press fit or a tiny amount of suitable adhesive after confirming smooth rotation. Keep adhesive out of the races. The pin should not bottom against the bearing or clamp its inner race axially; trim or change pin length if actual dimensions demand it. Both 3.05 and 8.05 mm printed bores are nominal CAD dimensions, not validated printed fits.

On receipt, measure and record: case length/width/depth; ear span and hole centers/diameters; output-axis offset from the case center; flange face from the back; boss and shaft projection; OEM horn arm thickness, radius and hole diameter; OEM center-screw thread/length. Adjust the parameters and rerun the generator before final printing. Check both servos: small manufacturing or variant differences matter at a 0.3 mm nominal cavity clearance.

The regenerated **provisional** assembly has no nominal volume intersections in `nominal_clashes.json`. `motion_check.json` checks 81 configurations at 20-degree increments across ±80 degrees, including the outboard bearing and pin envelopes; it does not check a continuous sweep or the real horns, fasteners, leads, ties or print tolerances. Passing this check is not a guarantee of a usable motion range or physical recovery.

The two bearings and pins are **new Rev B parts, not included in the user's reported orders**. The design should be reviewed against the delivered PTK horns before buying or printing the full arm. The lower post remains inside the 70 × 64 mm base footprint; the upper side bridge adds moving mass.

Regenerate with a separate CAD environment:

```sh
python3.12 -m venv .venv-cad
.venv-cad/bin/pip install cadquery==2.8.0 matplotlib
.venv-cad/bin/python cad/build_cad.py
.venv-cad/bin/python cad/check_motion.py
.venv-cad/bin/python cad/render_preview.py
```

Keep the CAD and training environments separate; their NumPy dependency ranges differ.
