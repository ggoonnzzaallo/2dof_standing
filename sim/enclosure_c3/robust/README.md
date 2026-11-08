> **Historical controller 0.8.** Current [0.9 uses ±90° and level-base straight holding](../upright/README.md). This directory retains its frozen v0.8 supervisor for playback. The following scores use the old base-only goal.

# C3: stronger recovery and varied retries

**7 November 2026 — controller 0.8 is uploaded and armed.** The user reports that the 0.7 policy repeats unsuccessful motions on the physical robot. This revision increases target speed, trains with broader mechanics variation and introduces a portable stalled-recovery supervisor. Physical recovery with the corrected 0.8 actor is awaiting operator observation. [Deployment](../../../firmware/policy_control/results/2026-11-07/deployment_0_8.json).

## Motion and retry changes

Joint targets remain **±80°**, approximately 789–2211 µs using the existing visual calibration. The incremental target cap increases from **0.06 to 0.10 rad per 20 ms**, so the maximum target rate is **3 → 5 rad/s** (about 172 → 286°/s). This is a commanded target-rate limit, not measured shaft speed. Travel beyond ±80° and actual servo end stops remain unmeasured. Genuine adjacent-body contacts stay enabled in simulation.

The actor retains 10 inputs, two outputs and 4,994 parameters. A small stateful [RecoveryStrategy.h](../../../firmware/policy_control/RecoveryStrategy.h) wraps it. If the base remains fallen for five seconds without recent meaningful improvement, it temporarily overrides actions with larger recovery sweeps. Continuing partial progress can delay a retry to nine seconds. Eight patterns alternate joint order and signs, with varied timing and target amplitude of about 70–80°. Cosine interpolation smooths the requested trajectory; the same target rate/range bounds apply. A base within about 10° cancels the active sweep so the policy can finish landing; one full second within 10° is needed to clear its failed-attempt memory. A base stuck 11.5–25° from level remains eligible for retries. The supervisor then returns to inference and can attempt another pattern if recovery fails again.

This is **bounded retry memory and pattern variation**, not online neural-weight learning or a guarantee of escape. The exact release C++ supervisor runs in both MuJoCo and the XIAO. After PPO training, the level/dwell criterion was tightened and separately revalidated on the matched cases and portable near-upright-stall regression. [Runtime refinement validation](results/runtime_validation.json) · [original training header](results/source/RecoveryStrategy_trained.h). Neural weights did not change for this guard refinement. The telemetry `retry` flag marks applied actions that came from the supervisor; non-retry actions are still checked against the exported actor. Previous-action observations contain the action actually applied. Sensor, timing, voltage and reboot-only 60-second inactivity stops remain active; retries do not clear faults or reset inactivity by themselves.

## More conservative mechanics

The frozen C3 exterior and mesh bundle are unchanged. A provisional **6 g** is added for wires/hot glue: 4.8 g base, 0.9 g middle and 0.3 g upper. Nominal mass is **94.162 g**, rather than 88.162 g. Each body inertia is scaled with its mass around its existing COM; actual wire/glue distribution has not been measured. [Model report](model_report.json).

Per randomized episode:

| Parameter | Range |
|---|---|
| Body mass and matching inertia | 0.93–1.15 × heavier nominal values |
| COM offsets | ±2 mm per coordinate/body |
| Sliding friction | **0.15–1.35**, broadened from 0.35–1.0 |
| Servo stall-torque model | **0.032–0.070 N·m** |
| Servo speed | **2.6–5.5 rad/s** |
| Servo proportional gain | 0.3–0.7 |
| Command delay | 0–3 policy ticks |
| Bent-joint starts | 40% of randomized resets, within ±1.15 rad |

The firmware IMU filter remains in the loop. Fallen resets include varied directions and inverted positions. Mass updates explicitly preserve the requested pose, and bent configurations are lifted only enough to remove initial ground penetration. The reward favors prompt stable-base recovery, adds a per-step time cost, substantially reduces effort/jerk penalties, and gives a large completion bonus. Episodes may last 30 seconds and continue across unsuccessful attempts; successful stable-base completion ends a training episode. The running firmware/playground keeps controlling after success.

## Training and matched evaluation

PPO warm-started the valid C3 0.7 actor, with a fresh critic, 3 environments, 512-step rollouts, batch 128, learning rate 8e-5, clip 0.12, gamma 0.995 and entropy coefficient 0.015. Observations are not normalized; training rewards are normalized.

| Additional PPO steps | Completed training episodes | Stable base /20 development cases | Mean capped recovery time |
|---:|---:|---:|---:|
| 0, faster runtime warm start | 0 | 20/20 | 2.281 s |
| **33,792, deployed** | **336** | **20/20** | **1.709 s** |
| 67,584, retained offline | 751 | 20/20 | 1.674 s |

Further optional updates were stopped after the saved 67,584-step stage. Unsaved interrupted updates are not used or counted. The deployed checkpoint remains the one already validated and armed; a 0.035 s change on 20 development cases is insufficient evidence for another hardware update. [Deployed checkpoint report](results/training_report.json) · [full saved-stage report](results/training_run_report.json) · [checkpoints](results/checkpoints) · [episode logs](results/episodes). Logs include only episodes completed by the final saved checkpoint.

Matched held-out simulation: 40 genuinely fallen randomized cases, seeds 71000–71039, heavier/broad-friction/weak-servo dynamics, 25-second horizon:

| Controller | Stable base by 5 s | Stable base by 25 s | Mean time, failures counted as 25 s | Faults |
|---|---:|---:|---:|---:|
| Previous 0.7 actor/runtime, 0.06 rad, no retries | 38/40 | 38/40 | 3.1565 s | 0 |
| Deployed corrected 0.8, 0.10 rad + retries | **40/40** | **40/40** | **1.7615 s** | 0 |

[Previous controller trials](results/held_out_previous_controller.json) · [final release trials](results/held_out_release.json). This is simulation, not physical reliability. Base success requires tilt <10°, angular speed <0.4 rad/s, base-floor contact and one-second dwell. Straight-arm posture is not required. No claim is made about eventual recovery outside the evaluated time or all possible surfaces. The broad held-out cases completed before retries were necessary; portable-header/actual-sketch tests separately verify stalled triggering, eight bounded large-sweep patterns and cancellation. Physical effectiveness of those escape patterns is not yet established.

## Invalid early stage and correction

An initial seed83 experiment called `mj_setConst` after placing the fallen robot. That function reset qpos to the reference pose, invalidating its training and evaluation claims. Its early 0.8 image was briefly uploaded/armed before the issue was caught, then PWM was stopped. The scores were explicitly withdrawn. The environment now saves/restores qpos/qvel and has a [regression](check_environment.py) asserting the requested upright, side, inverted and diagonal quaternions survive mass updates. Corrected training seed89 starts from the preserved valid 0.7 actor, not the invalid weights. [Invalid-stage marker](invalid_reset_stage/INVALID.json) · [superseded deployment record](../../../firmware/policy_control/results/2026-11-07/deployment_0_8_early_invalid.json).

## Run and reproduce

Open the **same heavier model, faster action integration and retry code** as the deployed controller:

```sh
.venv-sim/bin/mjpython sim/enclosure_c3/robust/play.py --tilt 90
```

Enter resets the full robot/controller; Space pauses; drag rotates; scroll zooms. Double-click a body, then Control + right-drag to apply a force. The old generic playground does not apply this revision's runtime changes; use the wrapper above.

```sh
.venv-sim/bin/python sim/enclosure_c3/robust/check_environment.py
.venv-sim/bin/python sim/enclosure_c3/robust/train.py --steps 65536 --seed 89 --out runs/c3_robust_reproduction
```

[Release summary](results/summary.json), [C export/parity](results/policy_robust.json), [actor](results/best.zip), [source snapshots](results/source), [firmware manifest](../../../firmware/policy_control/PolicyManifest.json). Controller 0.8's build is 89,364 bytes flash / 7,968 bytes static RAM; export parity error is 3.58e-7 over 1,000 vectors. Actual-sketch, retry-header, helper and corrected-pose checks passed before the corrected upload. Charging current/termination and actual physical recovery remain unmeasured/unconfirmed respectively.
