# Training and deployment pipeline

**Centered PTK revision:** `robot.xml` now places the battery below the deck, moves the joints to 42 and 87 mm, centers the two moving links, and uses nominal 13 g servo masses. This is a primitive approximation of the revised CAD, not measured mass or inertia. Servo speed, torque, lag and current behavior at 1S voltage have **not** been measured; `environment.py` retains exploratory placeholder dynamics. Do not train a transfer policy from those numbers until the delivered servos and assembled geometry are characterized.

Use **MuJoCo + Gymnasium + Stable-Baselines3 PPO**. The two-action, small-MLP problem does not justify changing to a GPU robotics stack before basic recovery is demonstrated. SB3 recommends CPU operation for its MLP PPO workloads and supports multiple environments. [Official PPO documentation](https://stable-baselines3.readthedocs.io/en/master/modules/ppo.html), [MuJoCo simulation documentation](https://mujoco.readthedocs.io/en/stable/computation/index.html).

## Supplied runnable starter

- `robot.xml`: free-base, two perpendicular hinges, floor contacts, approximate component masses and primitive collision shapes. Its main joint, paddle, battery, board and switch positions track the centered CAD. The battery tunnel, bearing cheeks, adapters, fasteners and contact details are simplified; it is **not an exact digital twin**. Parent-child collision filtering and physical joint limits must be reviewed as the geometry is finalized.
- `environment.py`: 2 ms physics, 20 ms policy steps; finite torque/speed/lag; command delay, mass, friction and IMU noise randomization; upright, side, diagonal and inverted resets.
- `train.py`: SB3 PPO with separate 64×64 tanh actor/critic, CPU and optional subprocess environments.
- `export_actor.py`: actor-only C export, no neural-network runtime required.
- `check.py`: environment validation, random rollout, short training smoke test, and compiled C-vs-SB3 parity test.
- `validation.json`: actual check results. No useful trained controller has been produced.

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
| 6–7 | Last commanded target angles divided by 1.3963 rad, clipped to ±1 |
| 8–9 | Previous clipped policy action |

Two outputs are clipped to ±1, multiplied by 0.06 rad and added to the stored joint targets each 20 ms. Clamp targets to ±1.3963 rad (±80°). Convert targets to calibrated servo pulse widths in firmware. Initial targets/actions are zero. Input scale/order, angle signs, timing and hidden-state initialization must match exactly.

There is no `VecNormalize` state to forget during export. The export preserves SB3's deterministic Gaussian mean and final action clipping; it does not introduce an extra output tanh. The actor contains 4,994 floats (19,976 bytes), about 4,864 multiply-accumulates per call plus tanh operations. It fits the proposed MCU comfortably in memory; measure worst-case execution time on the real firmware before committing to 50 Hz.

Actual joint angle and velocity are used for simulated servo dynamics and reward, **not policy observations**, since the selected three-wire PTK servos do not report them. Floor contact is likewise used to score success during training, not passed to the policy. It is fine for a simulator to use these privileged quantities for its reward: the deployed policy only runs inference and does not calculate that reward. A future feedback-servo upgrade requires a changed wiring/model/observation contract.

## Real training sequence

1. **Identify the hardware.** Weigh assemblies and measure COM. Record pulse-to-angle curves, sign, endpoints, no-load and loaded step responses, backlash, battery sag and current at 4.2/3.8/3.5 V. Fit servo dynamics and bound torque; stall torque is not continuous torque.
2. **Make a demonstrably recoverable mechanism.** Find slow scripted or short waypoint sequences for cardinal and diagonal falls. Search safe sequences in simulation, then test under supervision. If necessary change base width, paddle reach or contact shape. Preserve a simple scripted baseline.
3. **Build the simulation fidelity that matters.** Replace primitive contacts with a sensible decomposition of measured printed parts; do not use a single convex hull that fills the arm's open spaces. Match joint stops, base edges, battery deck and bearing-cheek contacts. Retain the floating root. Confirm real and simulated step responses before policy optimization.
4. **Use curriculum if scratch PPO stalls.** Start near upright, then side falls, then inverted starts. Optionally behavior-clone successful scripted trajectories into the actor, then call PPO `.learn(...)` to optimize further. The source project's search/demo-pretrain workflow is useful, but its saved model is not interchangeable with our changed geometry and observations. [Reference repository](https://github.com/homemadegarbage/SelfRisingRobot).
5. **Randomize within measured bounds.** The starter includes mass ±10%, floor friction 0.35–1.0, torque 0.045–0.070 N·m, speed 3–5 rad/s, gain, 0–40 ms command delay and sensor noise. These are placeholder ranges. Add measured backlash/deadband, COM uncertainty, battery-dependent behavior and observation delay before transfer. Avoid deliberately training on physically impossible torque.
6. **Evaluate separate from training.** Use held-out seeds; four side falls, four diagonals, inverted starts and multiple initial joint states; test several surfaces and voltages. Log recovery success within 10 s, recovery time, peak current, stalls and peak contact loads. Require sustained base uprightness, near-home arm, low angular velocity and floor contact. Do not count an airborne or tip-balanced instant as success.
7. **Deploy and compare logs.** Run IMU acquisition/fusion around 200 Hz, policy/PWM target update at 50 Hz. Export only the actor and compare known input/output vectors on the MCU. Then start with restricted motion and expand toward the validated envelope.

## IMU and sim-to-real details still to implement

**The current environment is a software starter, not yet sensor-faithful for transfer.** Its gravity observation comes from MuJoCo's exact base orientation plus noise, while the real robot has only one base-mounted accelerometer/gyro. Real hardware needs a quaternion-based gyro/accelerometer attitude filter and explicit sensor-to-base alignment; the environment must then use the same estimator or model its delay and dynamic errors before training a deployment policy. A normalized raw accelerometer reading is not gravity during a flip. Gate accelerometer correction during strong non-gravitational acceleration, and test recovery through 180-degree orientations. Avoid a roll/pitch formula that changes branches or saturates at 90 degrees. The IMU cannot directly see joint angle, contact or absolute yaw; upright recovery should not depend on absolute yaw.

The 10-input starter has no history or battery observation. If real servo lag creates partial observability, add a short observation history first (and update the exporter), or a battery-voltage feature after calibrating the ADC. A recurrent policy is an option, but makes deployment and reset behavior more complicated. Do not change observation dimensions only on one side.

Firmware board support, sensor filter, PWM calibration, battery sensing, arming, watchdog and servo-power sequencing remain to be implemented. The portable policy exporter is supplied and tested; a board-ready firmware image is not part of this prototype package.
