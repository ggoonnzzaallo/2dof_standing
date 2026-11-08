# Simulation and training

The current model is **C3 / controller 0.9**: the installed under-base enclosure, relocated electronics/IMU, ±90° joints, PPO recovery and a supervisor that straightens the arm on a level base. [Training recipe, checkpoints, results and clearance calculations](enclosure_c3/upright/README.md).

## Open the current playground

From the repository root, set up the Python environment once:

```sh
python3 -m venv .venv-sim
.venv-sim/bin/pip install -r sim/requirements.txt
```

On macOS, launch with `mjpython`:

```sh
.venv-sim/bin/mjpython sim/enclosure_c3/upright/play.py --tilt 90
```

| Control | Action |
|---|---|
| Drag / scroll | Rotate camera / zoom |
| Double-click a body, then Control + right-drag | Apply a force; release to watch recovery |
| Control + left-drag on a selected body | Apply torque |
| Enter / Backspace | Reset |
| Space | Pause/resume |

The playground uses the matching controller runtime and sends no robot commands. For model geometry and body grouping, see the [frozen C3 model](enclosure_c3/README.md#matched-model).

For repeatable video takes, use the [filming demo](../docs/FILMING_SIMULATION.md): three timed pushes, one-key restart and portrait MP4 export.

## How learning works

MuJoCo supplies contact and servo physics; Gymnasium supplies the environment; Stable-Baselines3 PPO refines the policy. The exported **10 → 64 → 64 → 2** actor runs onboard at **50 Hz**. Inputs are estimated base DOWN, gyro, commanded targets and previous applied actions. The servos have finite speed, torque and delay; actual joint angles are used in simulated physics/rewards, not policy observations.

The current experiment adds provisional wire/glue mass and randomizes friction, mass/COM, servo strength, speed and delay. A portable supervisor varies stalled attempts and holds neutral when level; it does not update weights online. New success scoring requires both a stable upright base and straight links. **48/50 fresh simulated cases** passed within 25 seconds; this is not a physical reliability rate. [Definitions, parameter ranges and evidence](enclosure_c3/upright/README.md#training-and-evaluation).

For reproduction or further training, follow the version-specific [current experiment](enclosure_c3/upright/README.md), its saved source snapshots and training report. The generic `sim/train.py` starter targets the original model, not C3. Geometry, observation scaling, actor export and firmware fingerprints must stay matched. Servo dynamics and some mass distributions remain estimates; see the [calibration plan](../docs/SIM_CALIBRATION_PLAN.md).

## Experiment history

| Experiment | Role |
|---|---|
| [Upright C3 / 0.9](enclosure_c3/upright/README.md) | Current: ±90°, straight-arm holding, upright-and-straight scoring |
| [Robust C3 / 0.8](enclosure_c3/robust/README.md) | Historical: heavier model, varied retries, ±80°, base-only scoring |
| [First C3 / 0.7](enclosure_c3/README.md) | Frozen installed geometry; earlier PPO actor |
| [C2 enclosure](enclosure/README.md) | Earlier enclosure candidate; not deployed |
| [Original recovery](recovery/README.md) | Demonstration-trained actor and original physical recovery |
| [Original starter](STARTER_GUIDE.md) | Generic scripts, original observation/action contract and calibration background |

These suites use different geometry and goals; compare results only within their stated evaluation conditions. Older pre-Onshape artifacts remain under `archive/`. Original geometry and mass assumptions are in [Onshape import](onshape/README.md) and [mass properties](mass_properties/README.md).

[Controller firmware](../firmware/policy_control/README.md) · [Recovery behavior ideas](../docs/RECOVERY_BEHAVIOR.md) · [All documentation](../docs/README.md)
