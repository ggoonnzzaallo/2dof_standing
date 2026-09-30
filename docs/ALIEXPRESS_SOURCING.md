# AliExpress shopping plan

AliExpress is an acceptable and potentially convenient **single marketplace checkout** for this project. Several sellers can still be involved, and shipping fees or delivery dates may differ per item. The repository's `BOM.md` preserves exact USA distributor links and the prices verified on 27 September 2026 as a baseline. It does **not** claim those prices apply on AliExpress.

Live AliExpress item pages were not accessible for verification in this work session. The browser's site-safety policy blocked AliExpress before any listing could be checked. The table below gives exact search phrases and acceptance criteria rather than invented product links, seller ratings, availability or prices. Record the chosen product URLs, variant and total delivered price here before ordering.

| Needed | Search phrase | Confirm in the listing before adding to cart |
|---|---|---|
| Controller | `Seeed XIAO nRF52840 Sense 102010469` | Buy the standard **Sense, SKU 102010469**: nRF52840, onboard **LSM6DS3TR-C** IMU, BQ25101 LiPo charger. The plain **102010448** lacks the IMU. **Sense Plus 102010694** retains it but adds unnecessary underside I/O pads; check mount and battery-pad clearance before substituting. Prefer Seeed's official store if identifiable. |
| Two identical servos | `FEETECH FT90M 3V 8.4V 20T` | FT90M model and published 3–8.4 V range; matching **20T** horns and center screws included. Check mounting-flange and output dimensions against `cad/README.md`. Do not silently choose FT90M-FB or generic SG90. |
| 1S battery | `1S 3.7V 500mAh 25C LiPo JST RCY` | Standard LiPo full-charge **4.2 V**, 1S, plausible discharge rating and measured pack dimensions at or below **59.5 × 19 × 7.5 mm** for the current CAD. Confirm connector type and polarity from photos, not just a title. A different dimension or plug requires a drawing/BOM change. |
| Battery mating lead | `JST RCY male pigtail 20AWG` | Mates physically and electrically to the selected battery. Check red/black polarity with a meter before connecting XIAO BAT pads. |
| Servo power switch | `Pololu 2810 mini mosfet slide switch LV` | Buy the **exact Pololu 2810** only if seller identity and board marking can be established. Otherwise use the linked Pololu source in `BOM.md`. A generic mechanical switch changes firmware cutoff behavior; document the substitution first. |
| Fasteners | `M2 x 8mm screws nuts washers set` | At least **8** matching M2×8 screws, nuts and flat washers. The current BOM buys a 25-set kit for spares. Output-horn center screws are separate; confirm them in the servo package or shorten two spare screws after fit measurement. |
| Cable ties | `2.5mm x 100mm nylon cable ties` | At least 6 usable ties and a few spares; the current print has 3.2 mm wide strap passages. |
| Heat shrink if absent | `heat shrink assortment 2mm 3mm 5mm` | Thin sleeves sized for the battery and servo-wire splices. |

**Skip the capacitor and signal resistors for the first order.** If loaded testing later shows power transients or signal back-powering, `BOM.md` lists exact optional parts and the symptoms that justify them.

Use a cart subtotal **with tax and shipping to your ZIP code** to check the $100 target. The revised $62.83 recommended parts subtotal comes from several USA sellers, not from an AliExpress cart. Do not choose a cheaper battery or servo until its voltage, stall-current behavior and dimensions are credible; those determine whether the robot can rise at all.

Chosen AliExpress item links and checkout total: **not yet verified**. Once selected, add exact item URLs and variant names above so future BOM changes remain reproducible.
