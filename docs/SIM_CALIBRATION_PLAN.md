# From the final CAD model to useful training

The final-CAD exploratory simulator is runnable. The next work is to establish the physical conventions and dynamics that the exported policy must share. No additional CAD export is needed unless the mechanism changes.

**Current working preference:** the user wants Codex to lead implementation, simulation experiments and testing autonomously. The learning options below are optional for later. Request the user's help only when a physical observation or measurement is necessary; do not make them choose ownership for routine work. Continue useful software work while physical calibration data is pending.

| Stage | What you do on the physical robot | What Codex can implement | Learning option |
|---|---|---|---|
| Review the model | Orbit it; confirm which pieces move with each joint and compare the zero pose with the assembled robot | Fix grouping/placements if needed; keep the structural upper axis authoritative | Run `sim/view.py --wiggle`, then inspect the three nested bodies in `sim/robot.xml` |
| Mass check | If a scale is available, weigh the complete assembled robot; measure accessible components only if convenient | Update `assumptions.json`, then recompute body COM/inertia and rerun checks | Change one assumed mass, rebuild, and inspect the change in `body_properties.json` |
| Joint map and clearance | With the arm supported, observe each joint separately from a fixed camera; identify neutral, positive direction and unobstructed endpoints | Add a calibration command/logger and save a pulse-to-angle map with independent limits for each joint | Derive angle from video or a protractor; implement the interpolation and review its plot |
| Servo dynamics | Record a few small and larger angle steps at known battery voltage, unloaded and with the assembled links; observe reversals | Fit delay, finite speed, tracking lag and deadband; compare simulated and held-out real traces | Fit one step trace yourself, then compare fitted and nominal curves |
| IMU alignment and estimator | Hold the base in known orientations, then rotate it slowly through side and inverted poses | Add IMU logging and a quaternion attitude filter; determine sensor-to-base rotation; run the same estimator in simulation | Start by predicting gravity-vector readings for six static faces, then verify the logs |
| Recoverability baseline | Later, observe supported or supervised trials and note actual contact/slip behavior | Search short waypoint sequences in simulation, record successful demonstrations and compare them with real motion | Write a simple two-waypoint sequence and evaluate cardinal/diagonal starts before adding an optimizer |
| RL and deployment | Review failure videos and help select representative initial poses/surfaces | Train demonstration-assisted/PPO policies, evaluate held-out cases, export actor C and verify MCU timing/parity | Own reward changes or evaluation scripts while Codex handles training infrastructure |

The [sensor-only commissioning firmware and CSV recorder](../firmware/imu_bench/README.md) are now implemented and compiled for the XIAO. Physical identity, timing and axes checks remain pending. The existing servo bench program is still available; calibrated pulse-to-angle reporting, actuator identification and the dynamic IMU estimator remain to be implemented after measurements.

## Concrete facts to record next

For each joint: a photo/video at its neutral pulse, the physical angle change produced by increasing pulse width, the accessible range on each side of neutral, and the points where wiring or printed parts begin to interfere. Both servo joints must use their own sign and limits. A nominal 1500 µs command alone does not establish an exact mechanical zero or 180° total travel.

For the mass model: complete weight is an easy first audit. Its difference from the current 73.92 g exploratory total is not automatically all wiring or all board mass; the total contains estimated servo/board/hardware values, and wiring is currently excluded at your request. Do not disassemble the robot solely to refine every gram before software work can continue.

For sensing: the XIAO board must be rigidly mounted to the base, in the same orientation used during calibration. Its raw IMU axes cannot be assumed to equal the CAD axes. The attitude filter must handle all orientations; dynamic acceleration during a flip cannot be treated directly as gravity.

For servo measurements: note the battery estimate and whether USB is attached, since charging and load can change the BAT-node reading. Keep the existing firmware voltage guard active and use the normal operating voltage range. Loaded behavior at one battery voltage should not be treated as a guaranteed torque/speed model across the full discharge range.

## Software work that can proceed independently

The model generator, visual review, geometry/inertia checks and Gymnasium interface are available now. Codex has also implemented trajectory search, audited demonstration collection, behavior cloning, PPO comparison, held-out evaluation and C-export checks. The [selected simulation-only neural controller](../sim/recovery/README.md) passes 100/100 broader held-out simulated trials. Hardware transfer still needs calibrated signs, endpoints, sensor observations and plausible servo dynamics; current adjacent-body collision exclusions also need review against the measured mechanical stops. Codex retains ownership of implementation and will ask only for the necessary physical observations.

The custom carrier PCB stays on the [hardware backlog](HARDWARE_BACKLOG.md); no PCB redesign is needed for these stages.
