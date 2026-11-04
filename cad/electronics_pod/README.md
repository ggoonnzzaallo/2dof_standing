# Lower enclosure — fit revision 3 (Rev C3)

**USB and battery refinements, 3 November 2026.** The previous C2 prints passed the user's fit check. This revision tightens the USB-C aperture and moves the battery outward, with the side wall replacing an end stop and a small flat relief on the rear screw boss. The new cup requires a fit check; the previous C2 approval does not automatically apply to these changes.

**[Download Rev C3 print package](rev_c3_print_fit.zip)** · [Cup STL](electronics_cup.stl) · [Cup STEP](electronics_cup.step) · [Interactive viewer](viewer.html) · [Fit instructions](PRINT_FIT_CHECK.md)

**Reprint the cup only. The C2 lid/servo mount is unchanged and still fits.** Its STL is byte-identical to the approved C2 file. The package includes it for new builds, but you do not need to print it again. The original [C2 ZIP](rev_c2_print_fit.zip) is retained; `rev_c_print_fit.zip` is an alias of the latest C3 package.

![Rev C3 enclosure and layout](preview.png)

## Requested changes

| Feature | Rev C3 | Approved Rev C2 |
|---|---|---|
| USB opening, width × height | **9.8 × 4.1 mm**, R0.6 corners | 14 × 7 mm |
| Opening allowance around CAD USB shell | About **0.43 mm per side / 0.445 mm top and bottom** | Much larger opening |
| Battery position | **7.3 mm rearward and 3.65 mm left**, same height/orientation | Centre `(0,14,-6.15)` mm |
| Battery end stop | Left cup wall, nominal **0.4 mm** gap | Separate free-standing stop |
| Other battery stops | Relocated front/right stops; rear rail joins rear wall | Original inboard rails |
| Rear-right screw boss | Small battery-side flat; **2.1 mm pilot wall** remains on that side | Full 7.6 mm round boss, 2.8 mm pilot wall |
| Screw axes, lid and servo frame | **Unchanged** | Two diagonal M2 × 10 mm screws |

The tighter opening is centred on the actual imported USB shell at CAD Y=−15.50733, Z=−6.545 mm. A corrected USB-only clearance envelope contains all source board mesh vertices while avoiding the old overly tall USB envelope. The PCB itself retains its previous containing envelope and locating stops. The actual USB plug overmould and printing tolerance still need a physical insertion test.

The battery centre is now `(-3.65,21.3,-6.15)` mm. Its 59.5 × 19 × 7.5 mm envelope clears the curved enclosure corner and the relieved boss. Checks also move the envelope ±0.25 mm in X and Y individually without interference. The boss relief removes only about 0.7 mm from its battery-side outer radius; the screw axis, 2.0 mm blind pilot and 8.6 mm depth are retained. A complete 6 mm-diameter structural collar around the entry/bore is checked over the full engagement depth. Do not tighten against or compress the battery pouch.

## Retained dimensions and features

The footprint remains **70 × 70 mm**, cup body depth **12 mm**, lid plate **2 mm**, closed package **14 mm**. Four shallow registration tabs enter the existing lid pockets. Cup walls/floor remain **1.2/1.6 mm**, with **R1 on the outside ground-contact edge**. The two existing M2 × 10 screws self-tap into the proven 2.0 mm blind bores; no nuts, inserts or coupon.

XIAO and Pololu positions are unchanged. Both boards keep their low **0.6 mm PSA lands**, nominal 0.4 mm insulating tape, locating stops and underside lead relief. Headers remain removed, with direct wires soldered to the boards. The switch window remains 2.6 mm high with its shallow PCB-edge relief. Only one Pololu is packaged. Wiring is still [Rev C](../../electrical/FROM_SCRATCH.md).

## Files and checks

- [Dimensioned top layout](layout.svg), [STEP assembly](assembly_review.step), [cup STEP](electronics_cup.step), [unchanged lid STEP](base_modified.step).
- [CAD validation](validation.json), [STL validation](stl_validation.json), [package manifest](fit_package_manifest.json), [review record](review_record.json).
- [C2 geometry/fit reference](fit_revision_2_reference.json) and [original first-fit reference](fit_revision_1_reference.json).

Cup and lid are valid single BRep solids and watertight, single-component STLs. Both STLs sit on the print bed at Z=0. Pairwise cup/lid/battery/board/Pololu/connector checks, USB envelope, slider travel, screw collar and battery-offset allowances pass. Existing frame gussets remain connected and unchanged. These are geometry checks, not a screw pullout, impact or printed cable-fit test.

The old C2 model, masses and trained actors remain unchanged. Its reproducible CAD inputs are frozen under [sim/enclosure/source/fit_approved_c2](../../sim/enclosure/source/fit_approved_c2), so generating a C2 simulator or joint view cannot silently pick up C3 geometry. Incorporate the battery translation and new sliced cup mass in the next simulation revision after fit confirmation. No firmware or physical robot commands are part of this CAD update.

## Reproduce

```sh
.venv-cad/bin/python cad/electronics_pod/build_pod.py
.venv-cad/bin/python cad/electronics_pod/build_preview.py
python3 cad/electronics_pod/validate_prints.py
python3 cad/electronics_pod/package_fit.py
```

Source Onshape and Pololu STEP files remain unchanged. The historical C2 ZIP is not overwritten by this generator.
