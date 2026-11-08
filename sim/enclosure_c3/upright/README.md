# C3: upright holding and ±90° travel

**Controller 0.9, 7 November 2026 — uploaded and armed.** Recovery now uses ±90° target limits, and a level-base mode smoothly straightens the arm. [Deployment](../../../firmware/policy_control/results/2026-11-07/deployment_0_9.json) · [release summary](results/summary.json).

## Keep the arm pointing up

The learned policy handles recovery. Once the IMU indicates a level, slowly rotating base, the portable supervisor eases both joint targets to calibrated **0° / 1500 µs**, at at most **2 rad/s**, then holds those targets. It does not let a learned resting bend persist on a flat base.

Level entry requires about 0.2 s within 8° and angular speed below 0.6 rad/s. Hysteresis returns to recovery beyond 12°, averaged angular speed above 1.2 rad/s, or a raw rate above 2 rad/s. Existing calibrated accelerometer samples are low-pass filtered with a 0.25 s time constant, gyro with 0.08 s; plausible near-1 g averages qualify level. This rejects table/contact vibration and permits straightening when the dynamic gravity estimate has a residual tilt error. The actor's gravity filter and 10-input observation contract are unchanged; no new sensor is added. The exact observer and supervisor header runs in the simulator and firmware.

This commands a straight pose. Three-wire servos provide no actual joint-angle readback, so horn alignment, backlash and load still affect physical accuracy. The mode operates while armed. The existing **60-second base-IMU inactivity lock** still detaches PWM; it is not overridden to hold the arm forever after shutdown.

Five randomized, initially bent, flat-base simulations straightened in **1.18–1.28 s** and stayed straight through the rest of each ten-second run. Actual simulated joint error after five seconds stayed below **0.11°**. That is a simulation result, not a physical accuracy measurement. [Flat hold evidence](upright_validation.json).

## Calculated travel clearance

The C3 geometry was swept with adjacent-body contacts active and the base lifted clear of the floor to isolate self-contact. Collision geometry is the existing convex decomposition with selective pivot-interface masks.

| Candidate target envelope | Static grid | Finding |
|---|---:|---|
| Both joints ±90° | **32,761 poses**, 1° spacing | No self-penetration reported |
| Lower ±90°, upper ±110° | **40,001 poses**, 1° spacing | No self-penetration reported |
| Both joints ±110° | 12,321 poses, 2° spacing | 2,109 poses penetrate >0.2 mm; deepest about 22.9 mm |

A finer single-axis diagnostic finds substantial lower-joint/base contact around **−91° / +93°**. Consequently, ±110° on both joints is not supported by the installed geometry. The upper joint has more structural room, but CAD clearance cannot determine the servo's internal end stops or its exact pulse-to-angle curve.

This release deploys **±90° on both**, approximately **700–2300 µs**, extrapolating the existing zero/±45° visual calibration. It does not deploy ±110° pulses. The model is a sampled structural calculation, not an assertion that the real mechanism has unlimited margin or a newly measured 180° servo stroke. Wires, hot-glue shapes, print variation and internal servo stops are not represented.

[Range sweep](range_audit.json) · [finer/asymmetric sweep](asymmetric_audit.json) · [scripts](audit_range.py). Eight nominal dynamic sideways recoveries also completed without non-floor self-penetration; peak actual simulated joint travel reached about 89.3°. [Dynamic contact audit](dynamic_contact_audit.json).

## Training and evaluation

The previous 0.8 PPO actor supplied the warm start. Expanding the normalized target observation from command/80° to command/90° requires multiplying the first policy layer's columns 6–7 by **90/80**, preserving its physical target interpretation before further learning. The [rescaled archive and recipe](results/source/warm_start.json) are preserved, along with a [reproduction helper](rescale_warm_start.py).

The selected experiment then completed **33,792 additional PPO transitions / 239 episodes**, with two checkpoints saved. On 20 development cases, upright-and-straight completion improved from 20/20 with 3.352 s mean to 20/20 with **2.905 s mean**. Earlier experiments using the uncorrected target normalization or previous level detector were not selected; their reports are retained under [experiments](results/experiments).

Mechanics randomization retains the heavier **94.162 g nominal** model, provisional extra 6 g wire/glue mass, per-body mass/inertia and COM variation, friction **0.15–1.35**, torque **0.032–0.070 N·m**, speed **2.6–5.5 rad/s**, and variable command delay. Recovery target rate stays **5 rad/s**, with larger 80–90° varied retry targets.

The new success criterion requires a base within **8°**, actual simulated joints within **0.12 rad (~6.9°)**, target commands within **0.05 rad**, angular speed below **0.4 rad/s** and a resting base for one second. Angular speed is smoothed over roughly 100 ms and a <=0.5 mm solver contact gap counts as resting, to reject stiff-contact numerical chatter. Joint positions and floor contact are scoring quantities, not policy inputs. These metrics differ from earlier base-only tests and must not be presented as a direct success-rate comparison.

On **50 fresh randomized fallen cases**, seeds 79000–79049, the selected controller completed **48/50** within 25 seconds, all qualifying successes by five seconds, with zero control faults. The other two ended with an upright base and near-zero targets/joints but did not satisfy the complete stability dwell; they remain misses. [Trials](results/held_out.json). Physical self-righting and straight-hold accuracy with 0.9 are not yet operator-confirmed.

## Software and deployment

The real-sketch checks pass for ±90° / 700–2300 µs, straight-target holding, varied retries and all previous stop/charge/startup guards. Portable tests cover hysteresis, spin/tilt return to recovery, table vibration with a biased gravity estimate, bounds and reset. Thirteen Mac-helper tests pass. C export versus SB3 error is **4.77e-7** over 1,000 vectors. Native build: **90,284 bytes flash / 8,000 bytes static RAM**. Actor/model/runtime fingerprints are verified before build and live arming.

Telemetry appends `override`, identifying either neutral-hold or recovery-sweep actions; host parity applies to non-overridden actor actions, with target/history/range/PWM checks on every row. Historical captures can use `--actor-header`, `--increment .06` and `--limit-deg 80` as appropriate. The old robust playground uses a frozen v0.8 header so current firmware changes do not alter its historical controller.

Open the current model and exact controller:

```sh
.venv-sim/bin/mjpython sim/enclosure_c3/upright/play.py --tilt 90
```

Enter resets, Space pauses, drag rotates, scroll zooms. Double-click a body and Control + right-drag to pull it.

[Selected actor](results/best.zip) · [checkpoints](results/checkpoints) · [training report](results/training_report.json) · [source snapshots](results/source) · [C export](results/policy_upright.json) · [manifest](../../../firmware/policy_control/PolicyManifest.json).
