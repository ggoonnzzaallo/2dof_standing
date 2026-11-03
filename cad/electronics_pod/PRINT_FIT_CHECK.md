# Rev C enclosure — print this first

Prepared **3 November 2026** for the existing **70 × 70 mm Onshape base**, XIAO nRF52840 Sense with long header pins **up**, one E-flite 500 mAh cell and **ONE Pololu 2810**.

**Print `electronics_cup.stl` only for the first fit check.** It is one cup with its floor integrated, 70 × 70 × 20 mm overall. The original robot base forms the lid. There is no service panel, bottom cover or connector-access window. The front wall has the slider opening; the left wall has USB access.

1. Import in **millimetres**, at **100% scale**. The STL already lies flat at Z=0; print **floor down, opening up**. Use PLA and your usual 0.2 mm profile; three wall lines are a reasonable fit-print starting point. Inspect the slicer around the USB opening, nut pockets and small wire-lacing bridges; use local support if your printer needs it. No claimed print weight is based on infill percentage alone.
2. With battery and USB **unplugged**, test the empty cup against the existing base. For this check, rest the base on top without drilling or fastening anything.
3. Place the **battery at the rear**, in its low locating stops. It must drop in without squeezing or scraping the pouch. The model leaves about 0.6 mm beneath it for thin insulating foam tape.
4. Place the **XIAO on the left**, USB toward the left opening and long header pins upward. Keep its previous orientation. Check underside solder/BAT wires and the short lower header tails against the pads/floor. The installed header/socket/wire stack must clear the original base when placed on top. Do not force either board onto printed supports.
5. Place **one Pololu at the front centre**, flat with components up and slider facing outward. Two rails under it accept about **0.4 mm insulating tape**; side/rear stops locate it without screws through its electrical pads. There is nominally **3 mm under the PCB** for solder and wire bends. Test actual board thickness and joints before adding tape permanently.
6. Flip the slider through **both complete positions** from outside, using a fingertip/fingernail. The nominal actuator protrudes about **0.6 mm** beyond the wall; the opening also clears an extra ±2 mm lateral lever allowance in CAD. Real access and retention still need your fit test.
7. Check USB insertion using your actual cable, then add the existing connectors/wires in the right-hand bay. The red blocks in the preview are only connector envelopes. Leave room to lift the original base for service; keep wires off the pouch, screw tips and moving joints.
8. Rest the original base on top again and check pin/wire clearance. For permanent attachment only after approving the fit: four M2×10 screws and M2 nuts on a **59 × 59 mm square**, plus the **12 × 10 mm wire slot** at X=15, Y=−14. `base_modified.step/stl` provide the drill/print reference; they are not needed for the initial board fit check.

Useful feedback: does each board drop in, does the slider have full usable travel, does USB insert, do solder/wires clear, and does the original base sit flat? Please keep the slicer's predicted cup mass for the later simulation update.

This is a **mechanical fit print**. The revised electrical harness is not installed, firmware 0.3 is not uploaded, and the enclosure's mass/contact changes are not yet in the trained model. The next electrical arrangement uses the Pololu as a battery master switch: **ON + USB + software PWM-off mode to charge; USB unplugged + OFF for storage**. Charge current and completion still need bench measurement.

See `preview.png`, `layout.svg`, `viewer.html` and `assembly_review.step` for placement. The controller/battery in the assembly are references, not printable solids. The printable STL is watertight and one connected component; selected CAD component-overlap checks passed. Actual solder joints, headers, cables, printing tolerances and fit remain unverified.
