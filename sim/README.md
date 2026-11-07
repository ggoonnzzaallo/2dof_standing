# Training and deployment pipeline

**V1 status, 7 November 2026:** a retained demonstration-trained actor runs on the physical robot and has demonstrated unassisted recovery, including battery operation without USB. Firmware 0.6 adds automatic battery-only startup. [Project summary](../docs/PROJECT_SUMMARY.md) · [Current controller](../firmware/policy_control/README.md).

## Choose the model and experiment

| Path | Purpose/status |
|---|---|
| `robot.xml`, `onshape/`, `recovery/` | Original final-Onshape geometry and the experiment supplying the deployed actor. Original masses total 73.922 g; adjacent-body exclusions remain a known limitation. |
| `enclosure/robot.xml`, `enclosure/` | Frozen fit-approved C2 enclosure, relocated electronics/IMU and corrected adjacent contacts. Offline candidate and results; not promoted to the robot. Model mass estimate 87.987 g. |
| `archive/` | Historical pre-Onshape primitive models/software checks. |

Latest printable CAD is C3, but the enclosure experiment deliberately uses frozen C2 inputs. No model builder silently updates the deployed actor. Current electrical design includes **one Pololu master switch**; the older original-geometry model predates the under-base enclosure.

The [original experiment](recovery/README.md) retained behavior cloning over a tested 67,584-transition PPO refinement. Its 100/100 broad simulated result is specific to that earlier suite. The [C2 experiment](enclosure/README.md) ran three PPO experiments totaling 202,752 transitions; its selected offline candidate scored 18/30 fresh randomized cases versus 8/30 for the original actor on the same new-model cases. These are different models/evaluations, not a single evolving hardware success rate.

Sliced print mass, component inertia assumptions and omitted wiring mass are documented in [original mass properties](mass_properties/README.md) and [C2 model report](enclosure/README.md#geometry-and-mass). Physical servo dynamics, power margins and impact behavior remain incompletely measured.

Use **MuJoCo + Gymnasium + Stable-Baselines3 PPO**. The two-action, small-MLP problem does not justify changing to a GPU robotics stack before basic recovery is demonstrated. SB3 recommends CPU operation for its MLP PPO workloads and supports multiple environments. [Official PPO documentation](https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html), [MuJoCo simulation documentation](https://mujoco.readthedocs.io/en/stable/computation/index.html).

## Supplied runnable starter

- `robot.xml`: generated final-CAD floating-base model, two perpendicular hinges, explicit body inertia and decomposed printed collisions. Current assumptions and contact exclusions are documented in [onshape](onshape/README.md); it is not a calibrated digital twin.
- `environment.py`: 1 ms physics, 20 ms policy steps; finite torque/speed/lag; command delay, mass, friction and IMU noise randomization; upright, side, diagonal and inverted resets placed just above the floor.
- `view.py`: interactive 3D MuJoCo review, optional slow joint motion and collision-shape display. On macOS use `mjpython`.
- `onshape/check_model.py` and `onshape/check_environment.py`: current offline checks with no training or robot commands.
- `train.py`: SB3 PPO with separate 64×64 tanh actor/critic, CPU and optional subprocess environments.
- `export_actor.py`: actor-only C export, no neural-network runtime required.
- `check.py`: environment validation, random rollout, short training smoke test, and compiled C-vs-SB3 parity test.
- `validation.json`: current environment check results; contact/geometry checks are in `onshape/validation.json`. Current trained-candidate evaluation/export results are in `recovery/results`; historical pre-Onshape smoke checks are in `archive/software_validation_before_onshape.json`.

From this package's root:

```sh
python3 -m venv .venv-sim
.venv-sim/bin/pip install -r sim/requirements.txt
.venv-sim/bin/python sim/check.py
.venv-sim/bin/python sim/train.py --envs 4 --steps 2000000 --out runs/ppo_seed1
.venv-sim/bin/python sim/export_actor.py runs/ppo_seed1.zip policy.h
```

The version pins record the tested environment rather than a claim that these are the newest releases. The default two million steps is a starting budget, not a convergence prediction. Repeat with independent seeds. The C compiler is required only for `check.py`'s host parity check.

## The servo is not an ideal angle source

The policy sends **target-angle changes**, not joint angles or motor torque. In `environment.py`, each command first passes through 0–40 ms of randomized delay. An internal servo target moves toward it at a finite rate. The simulated servo then compares that target with the **actual simulated joint angle and velocity** and applies a bounded torque; floor contact or gravity can make the joint lag, stall, or be pushed away from the target. This mirrors the division of work on the robot: the PTK servo closes its own position loop, while the XIAO only knows the angle it requested. Actual simulated joint angle is used inside the servo physics and training reward, **not as an input to the policy**.

The present **3–5 rad/s** speed, **0.045–0.070 N·m** torque, gain and delay ranges are placeholders, not measurements of PTK 7465 MG on one LiPo cell. The [related manufacturer's MG-D data](https://www.ptkhobby.com/en/sys-pd/234.html) only give speed at 5 V and above; they do not predict motion at 3.6–4.2 V while pushing against the floor. Before substantial training, mark a horn and film repeatable angle steps from a fixed camera at several battery voltages, first unloaded and then with a representative link/load. Fit command delay, joint angle versus time, steady tracking error and reversal deadband/backlash. Use a known lever/load and brief current measurements to bound usable torque without holding the servo stalled. Temporary video gives angle/speed measurements for calibration; the finished robot does not need joint sensors merely to calibrate the simulator. Compare real and simulated traces for held-out commands, then randomize parameters around the measured range. If large unobserved joint deviations still defeat recovery, consider feedback hardware and retrain with its angle readings.

## Observation/action contract

The 10 float32 inputs, in order, are:

| Indices | Value on both simulator and MCU |
|---|---|
| 0–2 | Unit DOWN vector in the base frame: `R_world_from_base.T @ [0,0,-1]`; upright is `[0,0,-1]` |
| 3–5 | Base-frame gyro in rad/s divided by 10, clipped to ±1 |
| 6–7 | Last commanded target angles divided by the configured joint limit (currently 80° ≈ 1.3962634 rad), clipped to ±1 |
| 8–9 | Previous clipped policy action |

Two outputs are clipped to ±1, multiplied by 0.06 rad and added to the stored joint targets each 20 ms. Clamp targets to the configured limits (currently ±80°, exploratory). Convert targets to calibrated servo pulse widths in firmware. Initial targets/actions are zero. Input scale/order, angle signs, timing and hidden-state initialization must match exactly. The limits will need separate values for each joint once measured.

There is no `VecNormalize` state to forget during export. The export preserves SB3's deterministic Gaussian mean and final action clipping; it does not introduce an extra output tanh. The actor contains 4,994 floats (19,976 bytes), about 4,864 multiply-accumulates per call plus tanh operations. It fits the proposed MCU comfortably in memory; measure worst-case execution time on the real firmware before committing to 50 Hz.

Actual joint angle and velocity are used for simulated servo dynamics and reward, **not policy observations**, since the selected three-wire PTK servos do not report them. Floor contact is likewise used to score success during training, not passed to the policy. It is fine for a simulator to use these privileged quantities for its reward: the deployed policy only runs inference and does not calculate that reward. A future feedback-servo upgrade requires a changed wiring/model/observation contract.

## Reproduction and optional further-training sequence

1. **Identify the hardware.** Review the [calibration plan](../docs/SIM_CALIBRATION_PLAN.md). Audit mass and COM where practical. Record pulse-to-angle curves, sign, endpoints, no-load and loaded step responses, backlash, battery sag and current across normal operating battery voltages while retaining the firmware guard. Fit servo dynamics and bound torque; stall torque is not continuous torque.
2. **Make a demonstrably recoverable mechanism.** Find slow scripted or short waypoint sequences for cardinal and diagonal falls. Search safe sequences in simulation, then test under supervision. If necessary change base width, paddle reach or contact shape. Preserve a simple scripted baseline.
3. **Build the simulation fidelity that matters.** The final printed CAD now has decomposed collision shapes and a floating root. Review adjacent-body exclusions and add calibrated joint stops or selective contacts so the simulated links cannot pass through each other in usable trajectories. Match real and simulated step responses and floor interactions before policy optimization.
4. **Use curriculum if scratch PPO stalls.** Start near upright, then side falls, then inverted starts. Optionally behavior-clone successful scripted trajectories into the actor, then call PPO `.learn(...)` to optimize further. The source project's search/demo-pretrain workflow is useful, but its saved model is not interchangeable with our changed geometry and observations. [Reference repository](https://github.com/homemadegarbage/SelfRisingRobot).
5. **Randomize within measured bounds.** The starter includes mass ±10%, floor friction 0.35–1.0, torque 0.045–0.070 N·m, speed 3–5 rad/s, gain, 0–40 ms command delay and sensor noise. These are placeholder ranges. Add measured backlash/deadband, COM uncertainty, battery-dependent behavior and observation delay before transfer. Avoid deliberately training on physically impossible torque.
6. **Evaluate separate from training.** Use held-out seeds; four side falls, four diagonals, inverted starts and multiple initial joint states; test several surfaces and voltages. Log recovery success within 10 s, recovery time, peak current, stalls and peak contact loads. Require sustained base uprightness, near-home arm, low angular velocity and floor contact. Do not count an airborne or tip-balanced instant as success.
7. **Deploy and compare logs.** Run IMU acquisition/fusion around 200 Hz, policy/PWM target update at 50 Hz. Export only the actor and compare known input/output vectors on the MCU. Then start with restricted motion and expand toward the validated envelope.

## IMU and sim-to-real status

The original default environment observes exact base DOWN plus simple noise. The filtered evaluator and C2 experiment instead run the portable firmware gravity estimator on simulated specific force and gyro, including the IMU site translation. Hardware acquisition, provisional measured sensor alignment/gyro bias, filtered DOWN, calibrated visual PWM signs and actor inference are implemented in the [current controller](../firmware/policy_control/README.md). This supersedes the earlier plan to implement the sensor stack before transfer.

The policy still has no joint feedback, contact sensor, battery observation or recurrent state. Servo lag/backlash/torque ranges and some mass distributions remain estimates; a successful physical recovery does not make the simulator a fully calibrated digital twin. The old model's adjacent-link exclusions are retained for provenance, while C2 uses selective pivot masks and genuine adjacent contacts.

Future training may add observation history, calibrated voltage dependence, trapped-state coverage and persistent recovery rewards. Those require coordinated model/export/firmware changes, not changing observation dimensions on one side. See [recovery behavior](../docs/RECOVERY_BEHAVIOR.md). No further training is required to reproduce the preserved V1 software state.
