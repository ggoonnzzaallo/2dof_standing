# Installed C3 enclosure — model and recovery training

**7 November 2026: trained, uploaded and armed.** The user confirms the latest tight-USB cup and battery against the side wall are installed. The original actor could not flip this revised physical build upright. Controller **0.7** now runs the selected C3-trained PPO actor, with a confirmed standalone handoff. Physical C3 self-righting is awaiting operator observation. The original actor and frozen C2 model/results are preserved. [Deployment record](../../firmware/policy_control/results/2026-11-07/deployment_0_7.json).

## Matched model

The [frozen installed CAD](source/installed_c3) is copied from the latest C3 generator output. This includes the 12 mm cup + 2 mm lid, outward battery position `(-3.65,21.3,-6.15)` mm, translated controller/IMU and one Pololu. Hinges and arm geometry stay at their user-confirmed axes. The closed exterior determines floor contact; ports and fixed internal cavities are omitted from collision geometry.

The unchanged lid uses its C2 slicer mass, 13.5517 g. Cup mass is provisionally **15.7485 g**, scaling the C2 slicer estimate by the C3/C2 CAD volume ratio **1.01124**. No C3-specific slicer mass or measured scale weight was supplied. The complete estimated mass is **88.1622 g**, and the upright COM is CAD `(-2.4408,3.0228,20.0628)` mm. Mass randomization remains enabled; this is not a measured physical mass distribution. [Configuration](configuration.json) · [inertia/component report](model_report.json).

The IMU site is `(-22.9590,-15.5000,-7.1700)` mm, with the previous measured sensor-to-base rotation retained. The site uses the board-envelope center proxy. Wiring/PSA mass remains omitted per the user's earlier instruction.

Adjacent-body contacts are active; only 50 convex pieces wholly within a 6 mm pivot sleeve use selective mating masks. No whole-body pair is excluded. Geometry checks pass: inertia, zero neutral false contacts, 81 sampled joint poses, deliberate out-of-range external contact, 10 placed-fall trials and 1,000 randomized-action steps. [Validation](validation.json) · [contact policy](contact_policy.json).

## Baselines on this exact model

Twenty familiar nominal/development cases, firmware IMU filter, 15 s per case:

| Actor | Stable base by 10 s | Stable base by 15 s | Historical strict straight-arm goal |
|---|---:|---:|---:|
| Deployed original-geometry actor | 15/20 | 16/20 | 10/20 |
| Offline C2 actor | 17/20 | 17/20 | 17/20 |

[Old deployed actor](baseline_deployed.json) · [C2 candidate](baseline_c2_candidate.json). These are development diagnostics, not held-out results or physical success rates. Stable base requires tilt <10°, angular speed <0.4 rad/s and base-floor contact for one second. The strict metric also requires each actual simulated joint within 0.18 rad of neutral.

Existing C2 waypoint plans were freshly replayed in C3: 8/9 nominal fallen requests recovered, all passed sampled adjacent-contact audit. They are a mechanism diagnostic, not a new policy or a claim that the old traces are C3 demonstrations. [Fresh replay report](waypoint_checks/report.json).

## Completed training experiment

`train.py` warm-starts the C2 actor into a fresh critic and runs PPO on C3. The policy/firmware contract stays **10 inputs, 2 outputs, 50 Hz, 0.06 rad increments, ±80°**, with the same actual firmware gravity filter. Actor observations are not normalized; only training returns are normalized.

The new reward prioritizes stable base recovery, gives neutral arm position a soft preference, and does not reward motion for its own sake. Episodes continue for up to 20 s after first recovery, with mild simulated impulses and some varied joint/target initial states. A failed ten-second attempt does not terminate the episode. Actual sensor/numerical faults still stop it. Initial thresholds/curriculum and reward constants are explicit in the source.

Training saves checkpoints around each requested 32,768 additional transitions, logs completed episodes and recovered/faulted episodes, and evaluates 20 standard development cases. Selection prioritizes stable base, then the historical strict metric. Additional random diagnostics use development seeds; final held-out seeds remain separate. Better simulated base recovery may leave a bent resting arm, so both metrics and final postures are retained.

```sh
.venv-cad/bin/python sim/enclosure_c3/build_model.py
.venv-cad/bin/python sim/enclosure_c3/check_model.py
.venv-sim/bin/python sim/enclosure_c3/train.py --check-env
.venv-sim/bin/python sim/enclosure_c3/train.py --steps 196608 --envs 3 \
  --out runs/enclosure_c3_persistent_seed71
```

The build wrappers reuse C2 machinery with explicit C3 inputs/output. They do not overwrite the old model, C2 results or the deployed actor. The source cup mass can be replaced in `configuration.json` when a C3-specific slice/measurement is available; rebuilding invalidates prior model hashes rather than silently reusing evaluations.

## Checkpoints and selection

The run completed **202,752 additional PPO transitions**, **206 completed episodes**, 191 episodes recovering at least once and five ending with a filter/numerical control fault. PPO rollout blocks account for the step count exceeding the requested 196,608. Seven checkpoints and training-return normalization snapshots are archived. Selection used only the 20 standard development cases; held-out seeds were evaluated after selection.

| Additional transitions | Stable base /20 | Strict straight-arm /20 |
|---:|---:|---:|
| 0 (warm start) | 17 | 17 |
| **33,792 (selected)** | **20** | **0** |
| 67,584 | 16 | 14 |
| 101,376 | 6 | 0 |
| 135,168 | 4 | 4 |
| 168,960 | 5 | 4 |
| 202,752 | 5 | 0 |

Later training degraded performance; the final checkpoint was not deployed. The selected checkpoint had **34 completed training episodes**. It commonly settles with the lower joint about −30° and upper about +5°. A base-only success must not be described as a straight-arm recovery.

## Held-out results

Fifty randomized cases, seeds 57000–57049, firmware gravity filter and 15 seconds per case, evaluated only after selection:

| Actor on C3 | Stable base by 10 s | Stable base by 15 s | Strict straight-arm by 15 s | Control faults |
|---|---:|---:|---:|---:|
| Selected C3 PPO | 49/50 | 49/50 | 0/50 | 0 |
| Original actor | 33/50 | 36/50 | 20/50 | 0 |

[Selected actor trials](held_out_selected.json) · [matched original actor trials](held_out_deployed.json). Seed 57000 did not recover within the evaluated horizon. No claim is made about eventual recovery beyond 15 seconds or physical reliability. A separate 30-case development diagnostic scored 30/30 stable base; it is not part of this held-out result.

## Saved artifacts and deployment

- [Selected actor](results/best.zip), [seven checkpoints](results/checkpoints), [episode logs](results/episodes), [return normalization](results/return_normalization).
- [Summary](results/summary.json), [training report](results/training_report.json), [unaltered original run report](results/training_report_original.json), [exact training source snapshot](results/training_source.py).
- [C actor header](results/policy_c3.h), [export parity result](results/policy_c3.json), [firmware selection manifest](../../firmware/policy_control/PolicyManifest.json).
- [Hardware deployment](../../firmware/policy_control/results/2026-11-07/deployment_0_7.json), [flat sensor capture](../../firmware/policy_control/results/2026-11-07/c3_flat_sensors_0_7.json), [standalone handoff](../../firmware/policy_control/results/2026-11-07/arm_0_7.json).

The archived export/training reports describe their offline stage; deployment status is recorded separately. `training_report.json` adds the explicit `config.filtered=true` playback contract; the untouched original report is preserved beside it. `PolicyManifest.json` pins hashes of the selected archive, C header, training report, XML and mesh bundle. Build and live-arm identity checks prevent accidental old-model deployment.

Controller 0.7 was uploaded and armed. The flat IMU check measured 2.49° estimated tilt without changing the mounting calibration. The user requested no further tests, so control was left running after standalone handoff. Physical C3 recovery and charging current/termination are not yet established.

To open the current actor and geometry together on this configured Mac (simulation only):

```sh
ROBOT_MODEL_PATH="$PWD/sim/enclosure_c3/robot.xml" .venv-sim/bin/mjpython sim/recovery/play.py \
  --model sim/enclosure_c3/results/best.zip --filtered
```

A matching simulator still does not establish physical recovery; servo dynamics, friction and real impact estimation remain uncertain.
