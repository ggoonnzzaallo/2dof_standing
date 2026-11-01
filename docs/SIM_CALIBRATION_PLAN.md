# From the final CAD model to useful training

The final-CAD exploratory simulator is runnable. The next work is to establish the physical conventions and dynamics that the exported policy must share. No additional CAD export is needed unless the mechanism changes.

| Stage | What you do on the physical robot | What Codex can implement | Learning option |
|---|---|---|---|
| Review the model | Orbit it; confirm which pieces move with each joint and compare the zero pose with the assembled robot | Fix grouping/placements if needed; keep the structural upper axis authoritative | Run `sim/view.py --wiggle`, then inspect the three nested bodies in `sim/robot.xml` |
| Mass check | If a scale is available, weigh the complete assembled robot; measure accessible components only if convenient | Update `assumptions.json`, then recompute body COM/inertia and rerun checks | Change one assumed mass, rebuild, and inspect the change in `body_properties.json` |
| Joint map and clearance | With the arm supported, observe each joint separately from a fixed camera; identify neutral, positive direction and unobstructed endpoints | Add a calibration command/logger and save a pulse-to-angle map with independent limits for each joint | Derive angle from video or a protractor; implement the interpolation and review its plot |
| Servo dynamics | Record a few small and larger angle steps at known battery voltage, unloaded and with the assembled links; observe reversals | Fit delay, finite speed, tracking lag and deadband; compare simulated and held-out real traces | Fit one step trace yourself, then compare fitted and nominal curves |
| IMU alignment and estimator | Hold the base in known orientations, then rotate it slowly through side and inverted poses | Add IMU logging and a quaternion attitude filter; determine sensor-to-base rotation; run the same estimator in simulation | Start by predicting gravity-vector readings for six static faces, then verify the logs |
| Recoverability baseline | Later, observe supported or supervised trials and note actual contact/slip behavior | Search short waypoint sequences in simulation, record successful demonstrations and compare them with real motion | Write a simple two-waypoint sequence and evaluate cardinal/diagonal starts before adding an optimizer |
| RL and deployment | Review failure videos and help select representative initial poses/surfaces | Train demonstration-assisted/PPO policies, evaluate held-out cases, export actor C and verify MCU timing/parity | Own reward changes or evaluation scripts while Codex handles training infrastructure |

We can pair on any row, or you can implement it and have Codex review the result. The command/logger work for physical calibration is not implemented by this document; the current bench firmware provides motion and battery telemetry, but no IMU acquisition or calibrated pulse-to-angle reporting yet.

## Concrete facts to record next

For each joint: a photo/video at its neutral pulse, the physical angle change produced by increasing pulse width, the accessible range on each side of neutral, and the points where wiring or printed parts begin to interfere. Both servo joints must use their own sign and limits. A nominal 1500 µs command alone does not establish an exact mechanical zero or 180° total travel.

For the mass model: complete weight is an easy first audit. Its difference from the current 73.92 g exploratory total is not automatically all wiring or all board mass; the total contains estimated servo/board/hardware values, and wiring is currently excluded at your request. Do not disassemble the robot solely to refine every gram before software work can continue.

For sensing: the XIAO board must be rigidly mounted to the base, in the same orientation used during calibration. Its raw IMU axes cannot be assumed to equal the CAD axes. The attitude filter must handle all orientations; dynamic acceleration during a flip cannot be treated directly as gravity.

For servo measurements: note the battery estimate and whether USB is attached, since charging and load can change the BAT-node reading. Keep the existing firmware voltage guard active and use the normal operating voltage range. Loaded behavior at one battery voltage should not be treated as a guaranteed torque/speed model across the full discharge range.

## Software work that can proceed independently

The model generator, visual review, geometry/inertia checks and Gymnasium interface are available now. We can also add plotting/log-analysis tools, define reset/evaluation cases and prepare trajectory-search tooling while measurements are being collected. Training a policy for exploration is possible, but a policy intended for hardware should use calibrated signs, endpoints, sensor observations and plausible servo dynamics. Current adjacent-body collision exclusions also need review against the measured mechanical stops.

The custom carrier PCB stays on the [hardware backlog](HARDWARE_BACKLOG.md); no PCB redesign is needed for these stages.
