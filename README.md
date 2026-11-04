# Self-righting arm — design package

**Using the assembled robot:** [Operating instructions](docs/OPERATING_INSTRUCTIONS.md) — disarm, check battery, charge and rearm from the Mac.

## Final Onshape CAD

The user-supplied final assembly and joint review are in [cad/onshape_import](cad/onshape_import/README.md). The corrected export is imported; a 0.57 mm residual servo-model offset is documented and the structural upper pivot remains the confirmed reference. The [MuJoCo model](sim/onshape/README.md) now uses that assembly, with a [simulated motion preview](sim/onshape/joint_motion.gif), explicit body inertia and decomposed printed collision shapes. Physical joint mapping, contact limits and servo/IMU calibration remain before hardware transfer.

**Enclosure fit revision 2:** [new cup and thin lid](cad/electronics_pod/README.md) reduce the closed package from 24 to 14 mm, add XIAO stops and low PSA lands, move the one Pololu to the opposite front corner, and use two existing M2×10 self-tapping screws with the model’s proven 2.0 mm screw bores. Headers are removed. The user confirms physical fit. The [revised MuJoCo model and joint controls](sim/enclosure/README.md) use the new slicer masses and IMU location; initial retraining and checkpoints are saved. The new candidate improves fresh randomized simulation recovery from 8/30 to 18/30, and remains offline pending further improvement and hardware validation.

The original arm slicer job gives **27.922 g of printed parts after removing supports**. The new cup/lid job gives **29.125 g** for those two replacement pieces; see the [enclosure mass report](sim/enclosure/README.md#geometry-and-mass) and [original mass properties](sim/mass_properties/README.md). The requested future carrier PCB is tracked in the [hardware backlog](docs/HARDWARE_BACKLOG.md).

Current purchased architecture: **XIAO nRF52840 Sense + two PTK 7465 MG servos + one 500 mAh, 1S LiPo**. The user reported all parts ordered on 1 October 2026; see [procurement status](docs/PROCUREMENT_STATUS.md). Train on a computer with MuJoCo and Stable-Baselines3 PPO; run the small exported actor on the XIAO. The **IMU and LiPo charger are already on the XIAO Sense board**, which is attached to the robot's base. **Rev C is prepared with ONE existing Pololu as the battery master switch**, software PWM-off charging and an under-base enclosure. D0/D1 remain PWM; D2, Pololu ON and SW are unused. No second switch board, boost converter, external IMU, servo driver, separate charger or extra electronic components are added. Physical rewiring and firmware upload remain pending; the last confirmed live harness is Rev B.

This is an assembled prototype, with both servo joints tested and Rev B wiring live. The final mechanical design is the user's Onshape assembly; earlier generated parts remain historical references. The simulator uses sliced printed masses and CAD geometry, while hardware mass/distribution, servo behavior and sensing still contain explicit assumptions. A [simulation-only neural recovery controller](sim/recovery/README.md) now passes 100/100 broader held-out simulated trials; its C actor was verified on the XIAO in [motor-disabled shadow firmware](firmware/policy_shadow/README.md), with virtual joint targets only. With the actual firmware gravity filter and simulated IMU readings, a newer fresh evaluation recovered in 26/30 trials. The first 500 hardware shadow frames matched host inference within 2.32e-7 and took about 1.2 ms per inference. Demonstration training outperformed the tested PPO refinement, so the earlier checkpoint is retained. The [bench firmware](firmware/README.md) provides terminal motion control, battery estimates, disarmed startup and timeout/heartbeat guards. Software stop/charge cannot disconnect servo power or idle drain. Rev C provides manual battery isolation with the slider; full OFF also requires USB unplugged. See the electrical guide for charging and commissioning checks.

On **2 November 2026**, the [onboard controller](firmware/policy_control/README.md) completed its first user-confirmed **unassisted sideways self-righting** trial, with additional manual disturbances during the 15-second run. It uses the unchanged actor at 50 Hz and the trained ±80° target range; inference peaked at 1.272 ms. Raw logs and operator observations are preserved. This is a first demonstration, not a reliability rate. The uploaded version 0.2 boots disarmed and adds explicit Mac arming; the user also confirmed **recovery on battery with USB unplugged**. [Standalone deployment records](firmware/policy_control/results/2026-11-02/standalone_0_2/deployment.json) preserve that observation. The broad adjacent-body collision exclusions are explicitly scheduled for correction before the next training pass.

## Arm from the Mac

For the full step-by-step procedure, see [Operating instructions](docs/OPERATING_INSTRUCTIONS.md).

With the battery, both servos and USB connected, place the robot near straight on a clear surface. From this repository folder:

```sh
./robot arm       # Moves to neutral, then starts onboard recovery
./robot status    # Reads state without stopping motion
./robot stop      # Stops PWM
./robot charge    # Firmware 0.3: latch PWM-off charge mode; switch ON + USB
```

After the arm command confirms **“Armed. Unplug USB”**, unplug USB for battery operation. Reconnect USB to use `status` or `stop`. For Rev C storage, unplug USB and slide OFF; for charging, keep ON + USB and run `./robot charge`. It boots disarmed after every reset/power cycle. The battery guard stops PWM but cannot operate the physical switch. Until rewiring, Rev B still requires battery and USB disconnected for full OFF. Firmware 0.3 is built/tested offline, not uploaded; arm/stop/status remain compatible with uploaded 0.2. See [standalone operation](firmware/policy_control/README.md#standalone-operation-02--arm-from-the-mac) for details and VS Code tasks.

## Package

- [Operating instructions: disarm, battery checks, charging and rearming](docs/OPERATING_INSTRUCTIONS.md)
- [One-piece under-base electronics cup and 3D layout](cad/electronics_pod/README.md) — [revised print-fit ZIP](cad/electronics_pod/rev_c2_print_fit.zip), lower cup + 2 mm lid, XIAO stops, corner switch and two M2 screws; no nuts or coupon
- [Current PTK parts list and fastener plan](BOM.md)
- [Ordered-parts status and incoming checks](docs/PROCUREMENT_STATUS.md)
- [Controller comparison and IMU location](docs/CONTROLLER_DECISION.md)
- [Servo choice versus SO-100 smart servos](docs/SERVO_DECISION.md)
- [Historical AliExpress shopping plan](docs/ALIEXPRESS_SOURCING.md)
- [Historical DigiKey sourcing audit](docs/DIGIKEY_SOURCING.md)
- [Wiring, commissioning, and design rationale](HARDWARE.md)
- [Complete wiring from scratch: twelve branches and both buses](electrical/FROM_SCRATCH.md), [one-page schematic PDF](electrical/REV_C_WIRING.pdf) ([PNG](electrical/REV_C_WIRING.png), [phone map](electrical/REV_C_PHONE_WIRING.png)) and [commissioning guide](electrical/README.md)
- [Onboard voltage monitoring and USB-C charging plan](HARDWARE.md#battery-monitoring-and-charging)
- [Power budget and brownout acceptance test](HARDWARE.md#power-budget-and-brownout-check)
- [Final Onshape assembly and 3D review](cad/onshape_import/README.md); [earlier parametric CAD and fit coupons](cad/README.md)
- [VS Code setup, first power-up and servo centering](firmware/README.md) — disarmed USB-controlled bench program
- [IMU commissioning and CSV logging](firmware/imu_bench/README.md) — first hardware-deployment stage, with servo outputs inactive
- [Onboard recovery controller](firmware/policy_control/README.md) — current uploaded firmware; disarmed boot, trained ±80° limits, Mac arming and standalone operation
- [Visual servo pulse-to-angle calibration](firmware/servo_calibration/README.md) — six measured visual references and signed PWM mapping
- [Calibrated IMU filter and motor-disabled neural policy checks](firmware/policy_shadow/README.md) — measured sensor/filter/inference results
- [Training and deployment pipeline](sim/README.md)
- [Current enclosure model, checkpoints and initial retraining results](sim/enclosure/README.md), [joint sliders](sim/enclosure/joints.html) and [persistent recovery/personality goals](docs/RECOVERY_BEHAVIOR.md)
- [Original-geometry neural recovery animation, results and saved actor](sim/recovery/README.md)
- [Current model checks](sim/onshape/validation.json), [Gymnasium checks](sim/validation.json), and [calibration/learning plan](docs/SIM_CALIBRATION_PLAN.md)

## Design decisions

The serial hinges are **perpendicular**: lower X axis, upper Y axis. Two parallel hinges would concentrate motion in one plane and make general sideways recovery much harder. The supplied reference XML also uses perpendicular axes. The base is free to translate and rotate; it is not attached to the table. Once recovered, the robot stands on a stable platform rather than continuously balancing on an edge. [Reference project](https://github.com/homemadegarbage/SelfRisingRobot), [project article](https://homemadegarbage.com/rl13).

The final Onshape base footprint is **70 × 70 mm**, with **153 mm** from base underside to upright tip. The pivot heights are CAD Z=24.4 and 61.4 mm, relative to an origin 2 mm above the base underside. The battery and XIAO sit on the base. The exploratory simulation totals **73.92 g**, including an assumed board mass and small-hardware allowance; wiring is excluded by request. The earlier 170 mm generated design and its mass estimates are historical.

The [XIAO Sense](https://wiki.seeedstudio.com/XIAO_BLE/) is 21 × 17.8 mm and combines an nRF52840, six-axis IMU, battery input and LiPo charger. It has enough memory for the provided 4,994-parameter actor: **19,976 bytes of float32 weights** plus small working buffers. This is inference only; training stays on the workstation. Select SKU **102010469**; similarly named XIAO boards have different sensors.

The reference [ATOM Matrix](https://docs.m5stack.com/en/core/ATOM%20Matrix) **also has its IMU onboard** and the author reports running the build on a 3.7 V cell. Its documented input is 5 V, and its board documentation does not list an onboard LiPo charger. For this version, the XIAO offers a smaller board footprint and integrated charging; the ATOM retains advantages for reproducing the author's firmware and Wi-Fi user interface. The [detailed comparison](docs/CONTROLLER_DECISION.md) separates verified specifications from prototype assumptions.

The [reference robot](https://homemadegarbage.com/rl13) used PTK 7465 MG servos from one 3.7 V LiPo; the author confirms operation without a boost converter in the article comments. This is direct evidence for the same kind of recovery task, but **not** a manufacturer's 1S operating guarantee. Confirm the exact received servo variant, test it at 4.2, 3.8 and 3.6 V, and update the CAD and simulation with measured dimensions and dynamics before relying on the design.

## Evidence and limits

All three robot-part STLs and four fit-coupon STLs pass watertight-mesh and single-connected-component checks; see `cad/stl_validation.json`.

The provisional PTK CAD solids export successfully; each printed part and fit coupon is one valid connected solid. The upright assembly has no unintended rigid-envelope overlaps. An 81-pose grid over both joints at 20-degree increments from −80 to +80 degrees found no clashes in the checked bodies, bearings and pins. This is **not** a continuous clearance certificate: actual horns, screw heads, nuts, leads, compliance and manufacturing tolerances still require inspection.

The earlier Gymnasium environment check, 1,500 randomized steps and short 512-step PPO training smoke test passed before the PTK geometry update. Exported C inference then agreed with SB3 deterministic inference to better than 1e-5 on 100 test observations. That smoke policy was discarded; the centered `sim/robot.xml` has only been loaded and briefly stepped in MuJoCo, not retrained or rechecked end-to-end.

The next physical milestones are: fit the supplied servo horns; measure travel/torque/lag at 4.2, 3.8 and 3.6 V; demonstrate a scripted rise from each major fall direction; update the model; then train and transfer. If scripted recovery is mechanically impossible from a resting pose, change the contact geometry before spending time on RL.

The USA distributor prices and listing availability in the [earlier FT90M estimate](docs/FT90M_BOM_HISTORY.md) were checked on **27 September 2026**. They are historical estimates, **not the actual cost of the ordered PTK build**. The capacitor and signal resistors remain optional diagnostic additions. The confirmed Pololu and battery order totals, and the still-unknown delivered costs of other purchases, are recorded in [procurement status](docs/PROCUREMENT_STATUS.md).
