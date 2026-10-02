# PTK 7465 MG incoming fit check

This sheet distinguishes **provisional CAD inputs** from dimensions measured on the two delivered non-W servos. Fill both measured columns before changing `build_cad.py` or printing the final base and link. The 7465W drawing and related MG-D page are useful family references, but neither establishes the exact dimensions of the purchased units.

| Feature (mm unless stated) | Current CAD input | Servo 1 measured | Servo 2 measured | Where used |
|---|---:|---|---|---|
| Main body length along mounting-hole line | 23.9 | — | — | `BODY_L` |
| Main body width | 12.0 | — | — | `BODY_W` |
| Main body depth, back to case top | 22.0 | — | — | `BODY_DEPTH` |
| Ear/flange overall span | 31.8 | — | — | `FLANGE_SPAN` |
| Ear mounting-hole pitch | 27.8 | — | — | `MOUNT_PITCH` |
| Mounting-hole diameter | 2.0 nominal | — | — | Check M2 clearance and flange holes |
| Output axis from body midpoint toward front end | 6.0 | — | — | `OUTPUT_OFFSET_Z` |
| Front flange face from case back | 18.4 | — | — | `FLANGE_FROM_BACK` |
| Ear thickness | 1.6 assumed | — | — | `FLANGE_T` |
| Shaft/spline outside diameter and tooth count | ~5.0, 25T | — | — | OEM horn only; no printed spline |
| Boss maximum diameter and projection from case | 11.0 × 4.4 assumed | — | — | `servo()` envelope |
| Shaft tip from case back | 30.1 nominal | — | — | `servo()` envelope |
| OEM horn face from joint center after seating | 16.5 assumed | — | — | `HORN_FACE` |
| OEM horn thickness, arm width and usable hole radius | not established | — | — | `cut_adapter()` slots and `horn` envelope |
| OEM center-screw thread and usable length | not established | — | — | Use supplied screw; do not force an M2 substitute |
| Servo pulse center, safe range and direction | 1500 µs trial center; ±80° design goal | — | — | Firmware and `sim/robot.xml` joint limits |

Print [servo-mount fit coupon](servo_mount_fit_coupon.stl) and [horn fit coupon](horn_fit_coupon.stl) first. Check the case clearance, ear-hole alignment and horn attachment without driving the arm. If either coupon needs filing to fit, change the CAD parameter rather than using filing as the final design. Record any interference from screw heads, leads or the rotating horn; the current motion check omits those items.
