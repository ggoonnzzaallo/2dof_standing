# Self-righting arm — Rev A design package

Current purchased architecture: **XIAO nRF52840 Sense + two PTK 7465 MG servos + one 500 mAh, 1S LiPo**. The user reported all parts ordered on 1 October 2026; see [procurement status](docs/PROCUREMENT_STATUS.md). Train on a computer with MuJoCo and Stable-Baselines3 PPO; run the small exported actor on the XIAO. The **IMU and LiPo charger are already on the XIAO Sense board**, which is attached to the robot's base. No boost converter, external IMU, servo driver board, or separate charger is planned.

This is a prototype design, not a proven self-righting product. **The current CAD and simulator were designed around FT90M servos and have not yet been updated or validated for the purchased PTK 7465 MG. Do not print final servo mounts or treat the existing simulation parameters as PTK measurements.** No physical robot has been assembled or tested, and no trained recovery policy is included. The low-voltage motor cutoff, USB charge interlock, and 100 mA charge-current configuration described in `HARDWARE.md` are firmware requirements, not implemented code yet; implement and test them before untethered battery runs or relying on in-robot USB charging for the 500 mAh pack.

## Package

- [Purchase list and exact fastener counts](BOM.md)
- [Ordered-parts status and incoming checks](docs/PROCUREMENT_STATUS.md)
- [Controller comparison and IMU location](docs/CONTROLLER_DECISION.md)
- [Servo choice versus SO-100 smart servos](docs/SERVO_DECISION.md)
- [AliExpress one-marketplace shopping plan](docs/ALIEXPRESS_SOURCING.md)
- [DigiKey-centered sourcing audit](docs/DIGIKEY_SOURCING.md)
- [Wiring, commissioning, and design rationale](HARDWARE.md)
- [Onboard voltage monitoring and USB-C charging plan](HARDWARE.md#battery-monitoring-and-charging)
- [Power budget and brownout acceptance test](HARDWARE.md#power-budget-and-brownout-check)
- [CAD assembly](cad/assembly.step), [preview](cad/preview.png), and [CAD/printing notes](cad/README.md)
- [Training and deployment pipeline](sim/README.md)
- [Software validation results](sim/validation.json) and [sampled CAD motion check](cad/motion_check.json)

## Design decisions

The serial hinges are **perpendicular**: lower X axis, upper Y axis. Two parallel hinges would concentrate motion in one plane and make general sideways recovery much harder. The supplied reference XML also uses perpendicular axes. The base is free to translate and rotate; it is not attached to the table. Once recovered, the robot stands on a stable platform rather than continuously balancing on an edge. [Reference project](https://github.com/homemadegarbage/SelfRisingRobot), [project article](https://homemadegarbage.com/rl13).

The current envelope is **70 × 64 × 132 mm upright**, with a 45 mm joint separation and a 60 mm upper paddle. Expect approximately **80–90 g assembled**, depending on printing, wiring and actual accessories. That is an estimate, not a measured weight. The parametric design allows shrinking after the recovery mechanics are demonstrated. The battery is a major footprint constraint; a smaller verified 1S pack is the first later optimization.

The [XIAO Sense](https://wiki.seeedstudio.com/XIAO_BLE/) is 21 × 17.8 mm and combines an nRF52840, six-axis IMU, battery input and LiPo charger. It has enough memory for the provided 4,994-parameter actor: **19,976 bytes of float32 weights** plus small working buffers. This is inference only; training stays on the workstation. Select SKU **102010469**; similarly named XIAO boards have different sensors.

The reference [ATOM Matrix](https://docs.m5stack.com/en/core/ATOM%20Matrix) **also has its IMU onboard** and the author reports running the build on a 3.7 V cell. Its documented input is 5 V, and its board documentation does not list an onboard LiPo charger. For this version, the XIAO offers a smaller board footprint and integrated charging; the ATOM retains advantages for reproducing the author's firmware and Wi-Fi user interface. The [detailed comparison](docs/CONTROLLER_DECISION.md) separates verified specifications from prototype assumptions.

The [reference robot](https://homemadegarbage.com/rl13) used PTK 7465 MG servos from one 3.7 V LiPo; the author confirms operation without a boost converter in the article comments. This is direct evidence for the same kind of recovery task, but **not** a manufacturer's 1S operating guarantee. Confirm the exact received servo variant, test it at 4.2, 3.8 and 3.6 V, and update the CAD and simulation with measured dimensions and dynamics before relying on the design.

## Evidence and limits

All four STL exports also pass a watertight-mesh and single-connected-component check; see `cad/stl_validation.json`.

The CAD solids export successfully; each printed part is one valid connected solid. The upright assembly has no unintended rigid-envelope overlaps. A 25-pose grid over both joints at −80, −40, 0, +40 and +80 degrees found no clashes in the checked bodies. This is **not** a continuous clearance certificate: actual horns, screw heads, nuts, leads, compliance and manufacturing tolerances still require inspection.

The Gymnasium environment check, 1,500 randomized steps and a short 512-step PPO training smoke test pass. Exported C inference agrees with SB3 deterministic inference to better than 1e-5 on 100 test observations. The smoke policy is discarded; that test establishes software operation, not learned recovery.

The next physical milestones are: fit the supplied servo horns; measure travel/torque/lag at 4.2, 3.8 and 3.6 V; demonstrate a scripted rise from each major fall direction; update the model; then train and transfer. If scripted recovery is mechanically impossible from a resting pose, change the contact geometry before spending time on RL.

The USA distributor prices and listing availability in `BOM.md` were checked on **27 September 2026** for the earlier FT90M design. They are historical estimates, **not the actual cost of the ordered PTK build**. The capacitor and signal resistors remain optional diagnostic additions. The confirmed Pololu and battery order totals, and the still-unknown delivered costs of other purchases, are recorded in [procurement status](docs/PROCUREMENT_STATUS.md).
