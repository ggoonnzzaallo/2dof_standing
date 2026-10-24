# PTK 7465 MG incoming fit check

Measure **both delivered servos** before printing full robot parts. The current model uses published 7465-family dimensions, not a verified drawing of the ordered non-W units. The four small STL coupons let you settle the interfaces cheaply.

| Feature | Current provisional CAD value | Servo 1 | Servo 2 |
|---|---:|---|---|
| Case length × width × depth | 23.9 × 12.0 × 22.0 mm | — | — |
| Ear span and mounting-hole pitch | 31.8 / 27.8 mm | — | — |
| Ear thickness and hole diameter | 1.6 / 2.0 mm | — | — |
| Output offset from case midpoint | 6.0 mm | — | — |
| Flange front face from case back | 18.4 mm | — | — |
| Boss diameter and projection | 11.0 × 4.4 mm | — | — |
| Output spline diameter and tooth count | about 5 mm / likely 25T | — | — |
| OEM horn face in the robot frame | +22 mm along motor axis | — | — |
| OEM horn thickness, arm width, usable hole positions | unknown; tab uses two provisional holes at ±3.3 mm, z+7.8 mm | — | — |
| OEM center-screw thread and length | unknown; use supplied screw | — | — |
| Rear lead and molded strain relief | unknown | — | — |
| Battery pouch length × width × thickness, connector bend | envelope 59.5 × 19 × 7.5 mm | — | — |
| MR83ZZ bearing OD × ID × width | nominal 8 × 3 × 3 mm | — | — |
| Rear support pin diameter × length | nominal 3 × 12 mm in CAD | — | — |

The [mount coupon](servo_mount_fit_coupon.stl) checks the exposed two-ear bracket. Confirm both ear screws can be installed without crushing the case or pinching the lead. The [horn-tab coupon](horn_fit_coupon.stl) checks the actual OEM horn and screw access: its center clearance is 7.0 mm and the two 2.2 mm lateral holes are **only placeholders**. Attach to the OEM horn; never force the spline or assume a generic SG90 pattern. The [bearing coupon](pivot_fit_coupon.stl) checks the 8.05 mm pocket. The [battery coupon](battery_tunnel_fit_coupon.stl) checks the 21 mm wide × 10 mm high tunnel; do not compress the LiPo pouch.

After adjusting `build_cad.py`, dry-assemble both joints unpowered. Seat the bearing by its outer ring only; check pin retention, coaxial alignment, free rotation, axial play, screw-head clearance and wire slack throughout the travel. Lightly side-load each link and inspect bridge roots, tabs and posts for flex or layer cracking. Check USB-C and slide-switch access at the base. Record the safe pulse endpoints and rotation direction for each servo before powering a full sweep.
