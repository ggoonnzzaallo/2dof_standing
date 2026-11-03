# Under-base electronics cup — fit-print revision

One **70 × 70 × 20 mm printed cup** hides the battery, XIAO and harness beneath the user's final Onshape base. The floor and walls are one solid; there is **no separate bottom cover or service panel**. The existing robot base acts as the lid. This revision follows the user's 2 November 2026 fit-review feedback.

The battery and servo disconnects remain reachable through a permanent front access slot, and USB-C remains accessible through the left wall. This retains the current charging and manual power-off procedure without extra electrical parts.

**Status: CAD checks passed; ready for a physical fit print, not yet a validated recovery configuration.** No training, firmware, electrical circuit, simulator, original STEP or purchased-BOM change is included. Test fit first, then update/evaluate the simulation before deciding how much retraining is needed.

## Files to use

- **[electronics_cup.stl](electronics_cup.stl)** — the single new part to slice and test fit. Its flat outside floor is already at Z=0, with the open side upward.
- **[electronics_cup.step](electronics_cup.step)** — editable solid for Onshape import.
- [Complete STEP assembly](assembly_review.step) — modified original base, cup, relocated electronics, arm and provisional header/connector envelopes. STEP preserves placed geometry, not native Onshape features/mates.
- [Modified original base: STEP](base_modified.step) / [STL](base_modified.stl) — four mounting holes and a rounded cable slot. Drill/machine the existing base using this reference, or print this replacement.
- [Interactive 3D viewer](viewer.html) — orbit, top layout, whole robot, visibility toggles and exploded view. Open the downloaded HTML in a browser; GitHub's file page does not execute it.
- [Dimensioned layout](layout.svg) and [CAD validation](validation.json).

![One-piece cup under the existing robot and its internal layout](preview.png)

## Layout and interfaces

| Item | Proposed arrangement |
| --- | --- |
| Cup | 70 × 70 mm footprint, 20 mm tall, 5 mm vertical corner radii. |
| Walls / floor | 1.8 mm walls, 2 mm integral floor; no bottom fasteners or seam. |
| Internal height | 18 mm from the floor surface to the original base underside. |
| Total robot height | Approximately 173 mm, up from 153 mm. |
| Battery | Existing 59.5 × 19 × 7.5 mm envelope across the rear/+Y side; low stops leave clearance rather than compressing the pouch. |
| XIAO | Left side with USB-C toward the −X wall. Translation only; retain the board's original orientation relative to the base. |
| Headers | Two rows of seven long pins pointing upward, toward the USB/component side, as confirmed by the user. Provisional 2.5 mm plastic bodies plus 6.2 mm exposed pins. |
| Wiring | Front/right bay, two lacing rails and envelopes for the existing RCY connection and both servo plugs. |
| USB window | 14 × 8 mm, centered on the socket; actual cable-overmold fit needs checking. |
| Front access | Open 34 × 15 mm notch, closed along its top by the original base when assembled. No removable panel. The open-top notch avoids printing a long bridge. |

The two servo leads still need external slack at the moving joints; the cup organizes existing wires rather than eliminating them. Keep wire coils and solder joints off the battery pouch and away from screw tips.

## Mounting and hardware

The cup attaches with **four M2×10 pan/socket-head screws and four M2 nuts**. Nuts slide into side-access pockets near the top of each corner boss. Check the actual nut fit before loading electronics. Thin insulating foam tape retains the battery and board; one existing small cable tie can retain the harness on the printed lacing rails. These are proposed mounting supplies, not changes to the purchased BOM.

Mounting holes are **2.4 mm diameter on a 59 × 59 mm square**, centered on the base. The rounded **12 × 10 mm cable slot** is centered at CAD (X=15, Y=−14) mm. The original plate is 4 mm thick, CAD Z=−2 to +2. The builder verifies full through-cuts remove only that plate material, leaving servo supports intact.

Use the modified STEP to orient the drilling/slot reference against the actual part. Do not drill with electronics or battery attached. Do not use the STEP assembly's negative Z coordinates for print-bed placement: the individual STL exports are shifted to put their lowest face at Z=0.

The cup's outside bottom is flat. All mounting screws enter from above through the original base. For major repairs, remove those four screws and lift the original base/arm away from the cup. Leave sufficient lead slack for separation while fully powered off.

## First fit-print sequence

1. Slice **electronics_cup.stl** with its floor flat and open side up. Review bridging/support at the 14 mm USB opening, nut pockets and lacing rails. PLA is suitable for this initial fit check. Record the slicer's predicted part mass; CAD solid-reference mass is not an infill-aware print prediction.
2. With battery and USB disconnected, test the nuts and check that the cup sits square against the original base. You can rest the unmodified base loosely on top for this first clearance check; drill the mounting holes/cable slot only after approving fit, or use the modified-base print.
3. Fit the battery without squeezing it. Thin foam tape underneath provides retention; low printed stops should not bite into its wrapper or lead exit.
4. Fit the XIAO on its small support pads with insulating tape, **keeping its previous orientation**. Check backside components, solder and BAT-pad wires clear the pads. Verify the pins and attached wire bends clear the original base above them, especially if sockets are fitted over the pins.
5. Route servo leads through the rounded slot with joint-motion slack, secure the harness in its bay and keep both complete servo plugs and the battery RCY pair reachable through the front notch.
6. Before closing the base, confirm you can physically disconnect the battery and both servos through that notch. Reposition leads or enlarge the notch if grip is difficult; do not rely on pulling individual wires.
7. Check USB plug insertion, access for reset/service, corner-screw tips and clearance through the joints' intended travel. Share any fit issues and the slicer/actual part mass before changing the simulation.

For routine charging, power off before changing connectors, disconnect both complete servo plugs through the front notch, then reconnect the battery and USB. Both servos stay unplugged while charging. With USB absent, battery disconnection is full OFF. This cup adds no electrical cutoff; follow the [operating instructions](../../docs/OPERATING_INSTRUCTIONS.md).

## Simulation and retraining after fit approval

**Expect a model update and possibly fine-tuning/retraining; a fit print comes first.** The original ground plane relative to the robot changes from CAD Z=−2 to Z=−22 mm. This changes resting poses, leverage against the floor and joint heights above it. Added plastic and relocated hardware change mass, center of gravity and inertia. Moving the IMU also changes the rotational acceleration measured at its position.

Keeping the XIAO's orientation unchanged preserves the existing axis mapping, but static sensor signs should still be rechecked after installation. A translation alone does not require learning a new axis rotation. There is no need to assume the policy must be trained from scratch: update the model, evaluate the current checkpoint, and fine-tune/retrain if its recovery performance is insufficient.

After the user approves fit and supplies the slicer/part mass:

1. Update MuJoCo collision geometry, floor contacts, mass/inertia, battery/board placement and simulated IMU location.
2. Correct the already-recorded [broad adjacent-body collision exclusions](../../docs/HARDWARE_BACKLOG.md) while updating the model.
3. Evaluate the existing policy over representative falls, disturbances and actuator uncertainty; retain results for comparison.
4. Fine-tune or retrain if needed, then repeat supervised physical recovery tests before battery-only use.

The successful trials with the old base do not validate this configuration. None of these model/training steps has been run for the cup yet.

## CAD checks and reproduction

The builder checks valid single-solid BReps, plate-cut volume, housing/base/battery overlaps, provisional headers and connector clearances, and a conservative PCB/socket envelope containing every imported board mesh vertex. The detailed source board BRep is invalid, so that enclosure clearance check uses a verified containing envelope instead of claiming exact solid validity for the electronics. Actual wire and connector dimensions still require physical inspection.

At uniform solid PLA density 1.32 g/cm³, the cup's CAD reference mass is about **29.0 g**. Slice the new part to get a print estimate; wall/floor count matters, so multiplying this value by infill percentage is incorrect. Hardware and wiring also contribute to the installed mass.

Using the existing CAD environment:

```sh
.venv-cad/bin/python cad/electronics_pod/build_pod.py
.venv-cad/bin/python cad/electronics_pod/build_preview.py
python3 cad/electronics_pod/validate_prints.py
```

The source is `cad/onshape_import/source/robot_onshape_third.step`. The builder does not rewrite the authoritative import artifacts. Header and connector models are packaging placeholders, not manufacturer CAD.
