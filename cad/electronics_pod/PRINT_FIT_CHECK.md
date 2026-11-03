# Enclosure fit revision 2 — Rev C2

Prepared **3 November 2026** from your fit photos. Uses your **M2 × 10 mm screws**, **no nuts**, and a **header-free XIAO** with directly soldered wires. Electrical Rev C remains unchanged; there is still only **ONE Pololu**.

## What changed

- XIAO locating tabs around the PCB, with about 0.3 mm clearance per side. Short tabs leave the castellated solder-pad rows open.
- Broad **0.6 mm-high PSA lands** under both boards instead of tall/narrow standoffs. Nominal 0.4 mm insulating PSA goes **on those lands**; the gaps between them relieve underside solder/wires. XIAO lands are two 4 × 8 mm strips; Pololu lands are two 12 × 3 mm strips. Check your actual tape and solder rather than forcing a board flat.
- Pololu at the **opposite front corner**, away from the XIAO. Existing plugs lie flat in the central wire-routing bay.
- Slider window **2.6 mm high**, down from 6 mm, plus the thin lower PCB-edge relief. Full slider motion and an extra ±2 mm lateral allowance clear in CAD.
- Cup walls **1.2 mm**, floor **1.6 mm**. Cup body **12 mm deep**; four registration tabs extend another 0.8 mm into the lid.
- Outside bottom edge has a **1 mm radius** to soften ground contact, with a flat central bottom.
- New lid plate **2 mm**, down from 4 mm. The original servo frame/axes are unchanged; four small top-side gussets overlap and connect to its walls. The lid underside stays flat for printing.
- **Two diagonal M2 × 10 screws** into blind plastic pilots. No nuts, nut pockets or two unused corner posts. Four shallow registration tabs/pockets locate the other edges.

The closed electronics package is **14 mm tall rather than 24 mm**. Footprint stays **70 × 70 mm** to match the existing robot and retain the battery fit. Cup plus lid CAD solid volume is **43.5% lower**; actual printed mass depends on slicing and must be recorded separately.

## Files to print

1. **`electronics_cup.stl`** — revised lower cup. Millimetres, 100% scale, **floor down/open side up**. STL overall height is **12.8 mm including the register tabs**. PLA at 0.2 mm layers is suitable for the next fit check. Inspect USB-window bridging in the slicer.
2. **`base_modified.stl`** — the **new thin lid with the existing servo frame**, flat underside down. It is a separate print, not another bottom cover. The old 4 mm lid is **not the matched lid** for this revision. Inspect the servo-frame bridges as for the original part.

Cup and lid are each one connected watertight solid and already sit on Z=0 in their STL exports. STEP files keep the assembly coordinate frame. There is **no screw-fit coupon**. The blind screw bores copy the original printed horn-bracket holes: **2.0 mm nominal diameter** in the supplied Onshape export, which the user confirms works with the existing screws. The new lid's through-clearance holes remain 2.4 mm.

## Unpowered fit sequence

1. Unplug **battery and USB**. Test the empty cup and lid first: four small tabs should enter their underside pockets, the lid should seat on the rim, and the two diagonal screw holes should align. No clip forcing is needed.
2. Put the battery in its accepted rear bay. Lateral stop locations are unchanged. Thin insulating tape under the pack should retain it without squeezing the pouch.
3. Locate the **XIAO on the left**, USB outward and original orientation retained. Headers are omitted. Put PSA on the low lands, keeping pads/components and underside BAT solder clear. Check the direct wires have a route through the gaps; enlarge the local relief rather than bending the board or crushing a joint.
4. Locate the **Pololu at the right front corner**, components up, slider out. PSA goes on its two low lands. **Solder VIN/VOUT/GND wires from the component side and route them upward**: there is now only about 1 mm under the board, not the previous 3 mm solder allowance. Do not use a through-hole solder mound as a mounting foot. ON/SW remain unwired.
5. Test full slider travel from outside and USB insertion with the actual cable. The nominal lever projects about 0.6 mm beyond the wall; smaller vertical access needs your real check.
6. Lay the existing battery/servo plugs flat and route wires in the centre. The red CAD blocks are conservative envelopes, not exact connector models. Check the lid closes without pressing solder or wires and that the 12 × 10 mm lid cable slot carries the servo leads without pinching.
7. Install **two existing M2 × 10 mm self-tapping screws** into the diagonal bosses. The lid has 2.4 mm clearance holes; cup bores are **2.0 mm × 8.6 mm deep**, matching the proven screw-hole diameter elsewhere in the model and giving nominally 8 mm engagement plus 0.6 mm tip clearance. No nuts. Snug by hand as with the other printed joints; back-turn to find the formed thread when reopening. Retention of this new two-screw enclosure still needs a physical check.

Please report board/PSA seating, slider motion, USB fit, direct-wire headroom, lid flatness and screw feel. Keep the slicer's cup and lid mass estimates for the later simulation update.

This is still a **fit print**, not a structural load certificate or recovery validation. The previous photo fit confirmed the battery bay, but not this lower/wired package. No electrical rewire, firmware upload, robot movement, new training or IMU calibration is performed by these CAD changes.
