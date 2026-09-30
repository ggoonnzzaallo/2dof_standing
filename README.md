# Self-righting arm — Rev A design package

Recommended architecture: **XIAO nRF52840 Sense + two FEETECH FT90M servos + one 500 mAh, 1S LiPo**. Train on a computer with MuJoCo and Stable-Baselines3 PPO; run the small exported actor on the XIAO. The **IMU is already on the XIAO Sense board**, which is attached to the robot's base. No boost converter, external IMU, servo driver board, or separate charger is required.

This is a concrete prototype design, not a proven self-righting product. CAD exports and software checks are supplied. No physical robot has been assembled or tested, and no trained recovery policy is included.

## Package

- [Purchase list and exact fastener counts](BOM.md)
- [Controller comparison and IMU location](docs/CONTROLLER_DECISION.md)
- [AliExpress one-marketplace shopping plan](docs/ALIEXPRESS_SOURCING.md)
- [Wiring, commissioning, and design rationale](HARDWARE.md)
- [Power budget and brownout acceptance test](HARDWARE.md#power-budget-and-brownout-check)
- [CAD assembly](cad/assembly.step), [preview](cad/preview.png), and [CAD/printing notes](cad/README.md)
- [Training and deployment pipeline](sim/README.md)
- [Software validation results](sim/validation.json) and [sampled CAD motion check](cad/motion_check.json)

## Design decisions

The serial hinges are **perpendicular**: lower X axis, upper Y axis. Two parallel hinges would concentrate motion in one plane and make general sideways recovery much harder. The supplied reference XML also uses perpendicular axes. The base is free to translate and rotate; it is not attached to the table. Once recovered, the robot stands on a stable platform rather than continuously balancing on an edge. [Reference project](https://github.com/homemadegarbage/SelfRisingRobot), [project article](https://homemadegarbage.com/rl13).

The current envelope is **70 × 64 × 132 mm upright**, with a 45 mm joint separation and a 60 mm upper paddle. Expect approximately **80–90 g assembled**, depending on printing, wiring and actual accessories. That is an estimate, not a measured weight. The parametric design allows shrinking after the recovery mechanics are demonstrated. The battery is a major footprint constraint; a smaller verified 1S pack is the first later optimization.

The [XIAO Sense](https://wiki.seeedstudio.com/XIAO_BLE/) is 21 × 17.8 mm and combines an nRF52840, six-axis IMU, battery input and LiPo charger. It has enough memory for the provided 4,994-parameter actor: **19,976 bytes of float32 weights** plus small working buffers. This is inference only; training stays on the workstation. Select SKU **102010469**; similarly named XIAO boards have different sensors.

The reference [ATOM Matrix](https://docs.m5stack.com/en/core/ATOM%20Matrix) **also has its IMU onboard** and the author reports running the build on a 3.7 V cell. Its documented input is 5 V, and its board documentation does not list an onboard LiPo charger. For this version, the XIAO offers a smaller board footprint and integrated charging; the ATOM retains advantages for reproducing the author's firmware and Wi-Fi user interface. The [detailed comparison](docs/CONTROLLER_DECISION.md) separates verified specifications from prototype assumptions.

The [PTK 7465MG listing](https://kwadyote.com/product/ptk-7465-mg-servo-metal-gear-9g-micro-servo-for-planes-glider-rc-car-helicopter/) specifies 4.8–8.4 V. Although examples run it from a LiPo cell, 3.5–4.2 V is outside that published range. The [FT90M datasheet](https://evelta.com/content/datasheets/501-FT90M.pdf) explicitly allows 3–8.4 V, making it the better supported no-boost choice. Its lower torque still needs a loaded recovery test.

## Evidence and limits

All four STL exports also pass a watertight-mesh and single-connected-component check; see `cad/stl_validation.json`.

The CAD solids export successfully; each printed part is one valid connected solid. The upright assembly has no unintended rigid-envelope overlaps. A 25-pose grid over both joints at −80, −40, 0, +40 and +80 degrees found no clashes in the checked bodies. This is **not** a continuous clearance certificate: actual horns, screw heads, nuts, leads, compliance and manufacturing tolerances still require inspection.

The Gymnasium environment check, 1,500 randomized steps and a short 512-step PPO training smoke test pass. Exported C inference agrees with SB3 deterministic inference to better than 1e-5 on 100 test observations. The smoke policy is discarded; that test establishes software operation, not learned recovery.

The next physical milestones are: fit the supplied servo horns; measure travel/torque/lag at 4.2, 3.8 and 3.6 V; demonstrate a scripted rise from each major fall direction; update the model; then train and transfer. If scripted recovery is mechanically impossible from a resting pose, change the contact geometry before spending time on RL.

The USA distributor prices and listing availability in `BOM.md` were checked on **27 September 2026**. Recommended purchased parts total **$62.83**, before shipping, tax and any tariff. The capacitor and signal resistors are optional diagnostic additions, not first-order requirements. Heat shrink is a $4.95 optional purchase if absent from the bench. A delivered total below $100 is plausible but is not a checkout quote; multiple sellers' shipping can consume the remaining margin. AliExpress can consolidate shopping into one marketplace, but its live listings and prices have not been verified; use the [shopping criteria](docs/ALIEXPRESS_SOURCING.md) before selecting substitutes.
