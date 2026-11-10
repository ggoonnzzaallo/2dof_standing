# Rev C3 — printing and fit checks

The current C3 enclosure was confirmed installed on 7 November 2026. For a new build, print the cup and lid supplied here. For an upgrade from C2, only reprint the cup: its USB opening, battery location/stops and battery-side screw-boss relief changed. Use two M2 × 10 mm screws into plastic; no nuts or coupon.

## Print

Print **`electronics_cup.stl`**, millimetres, 100% scale, floor down/open side up. It is one connected watertight solid with Z=0 on the bed; total height is 12.8 mm including the 0.8 mm registration tabs. Inspect the USB bridge and R0.6 opening corners in the slicer. Keep your previous successful PLA settings and record the new cup's sliced mass.

Print **`base_modified.stl`** for a new build. It is byte-identical to the approved C2 lid, so an existing C2 lid needs no reprint. The four printed arm components are in the [complete robot STEP](assembly_review.step); export those bodies from your CAD tool if needed.

## Unpowered fit

1. Disconnect **battery and USB** before transferring components. Inspect/deburr the USB aperture without changing its size unless the cable test shows it is needed.
2. Seat the header-free XIAO on the same low insulated PSA lands and stops, USB outward. Check insertion of your actual USB cable through the **9.8 × 4.1 mm** opening; nominal shell clearance is about 0.43 mm sideways and 0.445 mm vertically. Do not use the plug to force the board into position. Headers, PCB location and underside BAT-wire routing are unchanged.
3. Place the battery **7.3 mm toward the rear and 3.65 mm toward the left wall**. The left wall replaces one end stop, and the front/right stops and wall-connected rear rail locate the other directions. Keep thin insulating retention tape; the pouch should drop in without bending, squeezing or contacting a sharp edge.
4. Inspect the relieved rear-right screw boss beside the battery. Its screw axis and bore are unchanged; clearance must remain when the pouch and tape are seated. Route the battery lead into the centre bay, away from the screw and lid rim.
5. Transfer the Pololu to its unchanged front-corner lands/stops. Route existing plugs flat in the centre, check switch travel, and close the original C2 lid. Check that wires and connector overmoulds are not pinched.
6. Reuse the two M2 × 10 screws. Find their existing formed threads by back-turning and snug by hand; check the lid seats flat and the battery remains free of screw/boss pressure.

The 70 mm footprint, 12 mm cup body, 2 mm lid, ground-edge radius, switch position and wiring are unchanged. Verify USB/cable and battery/boss fit on each new print. No electrical testing, upload or motion is performed by the CAD scripts.
