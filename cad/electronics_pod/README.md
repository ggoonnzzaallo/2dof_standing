# Rev C — one-piece enclosure with ONE Pololu

**Fit-print revision, 3 November 2026.** Packages the existing XIAO Sense, 500 mAh battery and **one** purchased Pololu 2810 beneath the confirmed 70 × 70 mm Onshape base. The Pololu will be the battery master switch; no second switch board or additional electronic components are included.

**Start here:** [print and fit-check instructions](PRINT_FIT_CHECK.md). Print only [electronics_cup.stl](electronics_cup.stl) for the first unpowered board fit. The original base can rest on top without drilling for this check.

![Revised enclosure and layout](preview.png)

## Files

- [Print-fit package ZIP](rev_c_print_fit.zip) — cup STL/STEP, assembly STEP, layout, preview and fit instructions.
- [Cup STL](electronics_cup.stl) and [editable solid STEP](electronics_cup.step).
- [Interactive 3D viewer](viewer.html): orbit, top layout, front-switch view, whole robot, visibility and explode controls.
- [Dimensioned top layout](layout.svg) and [assembled STEP](assembly_review.step).
- [Modified original base STEP](base_modified.step) / [STL](base_modified.stl): mounting holes and cable-slot reference for later installation.
- [BRep/packaging checks](validation.json) and [STL checks](stl_validation.json).

## Packaging

| Item | Position / allowance |
|---|---|
| Cup | **70 × 70 × 20 mm**, one printed part with 1.8 mm walls and 2 mm integral floor. Existing base is the lid. No service panel or connector-access notch. |
| Battery | Rear bay, nominal 59.5 × 19 × 7.5 mm. Low stops and thin insulating tape; never compress the pouch. |
| XIAO Sense | Left bay, USB through left wall. Original orientation retained; long header pins point **up** as confirmed. Installed header/socket/wire height needs checking. |
| Pololu 2810 | **One**, front-centre, PCB horizontal with components up. Supplier STEP PCB is 15.24 mm square. Side/rear locating stops, insulated tape on two support rails, nominal 3 mm underside solder space. No screws through electrical pads. |
| Slider access | Front opening 10 × 6 mm plus a shallow PCB-edge clearance. Actuator extends about 0.6 mm beyond the outer wall. Extra ±2 mm lateral lever clearance checked in CAD; full travel and fingernail access need real testing. |
| USB opening | 14 mm wide × 8 mm high on the left wall. Check the actual cable overmould and reset access. |
| Connectors / wires | Existing RCY and two servo plugs in the right-hand bay. Internal service only by lifting the base; no routine connector handling for the selected charge workflow. |

Cup mounting remains four **M2×10 screws and four M2 nuts**, with 2.4 mm through-holes on a **59 × 59 mm square**. Top-loaded screws pass through the original 4 mm base plate into cup nut pockets; there are no bottom-cover screws. The 12 × 10 mm rounded cable slot is at CAD X=15, Y=−14 mm. Use the modified base as a reference only after the first fit approval.

The STL is already positioned floor-down at Z=0. CAD STEP files retain the existing assembly frame (cup floor underside Z=−22, original base underside Z=−2). Overall robot height becomes about 173 mm. The revised cup's **solid-PLA reference** is 30.3 g at 1.32 g/cm³; this is not a sliced 20%-infill print-weight estimate.

## Wiring and software status

See the [complete Rev C schematic](../../electrical/README.md). Battery positive goes to Pololu VIN; VOUT feeds the common XIAO BAT+/servo-positive bus. Ground is common, D0/D1 remain PWM and D2/ON/SW are unconnected. The physical slider is the only switch control.

The chosen behavior is **ON + USB + `./robot charge` to charge**, with PWM stopped but servo power still present; **USB unplugged + OFF for storage**. Firmware 0.3 is built and tested offline, not uploaded. Rev C wiring, through-switch charging, servo idle current and charge termination are not physically verified. The last confirmed live harness remains Rev B. Do not mistake a mechanical fit approval for electrical commissioning.

## Validation and reproduction

The cup and modified base are valid single-solid BReps and export as watertight, one-component STLs. The builder checks selected rigid overlaps, a containing envelope for the invalid detailed controller BRep, provisional headers/connectors, one actual Pololu solid and the projected slider-access allowance. Wire bends, solder, connector dimensions, adhesive retention and printing tolerance still require your fit test.

```sh
.venv-cad/bin/python cad/electronics_pod/build_pod.py
.venv-cad/bin/python cad/electronics_pod/build_preview.py
python3 cad/electronics_pod/validate_prints.py
python3 cad/electronics_pod/package_fit.py
```

The original Onshape geometry remains untouched. The Pololu source is the user-supplied `mini-mosfet-slide-switch-with-reverse-voltage-protection.step`, copied to [source/pololu_2810.step](source/pololu_2810.step); see [manufacturer documentation](https://www.pololu.com/product/2810). Source hashes and tested offsets are recorded in validation.json.

## After fit approval

Record sliced/actual cup mass, confirm the XIAO orientation and update the simulation's floor contacts, masses/inertias and IMU position. Correct the [known collision exclusions](../../docs/HARDWARE_BACKLOG.md) during that model update, evaluate the current policy, then fine-tune/retrain if needed. No simulation or model weights were changed for this fit-print revision.
