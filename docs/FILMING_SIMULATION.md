# Film the simulated robot

A repeatable **22-second** demonstration for Shorts: start upright, receive three brief pushes, recover using controller 0.9, then stop at the final pose. It uses the current C3 model, IMU observer and recovery supervisor. Only the external pushes are scripted; the joints are controlled by the policy/supervisor throughout. No hardware commands are sent.

## Open the live demo

From the repository root, with the [simulation environment installed](../sim/README.md#open-the-current-playground):

```sh
.venv-sim/bin/mjpython sim/enclosure_c3/upright/filming_demo.py
```

The window opens **paused**. Adjust the camera and start your screen recording, then press **R**. The first push happens after a three-second lead-in.

| Key / mouse | Action |
|---|---|
| **R**, Enter or Backspace | Reset the robot, observer, controller history, random seed and sequence clock; play from the beginning |
| **Space** | Pause/resume without restarting |
| Drag / scroll | Orbit / zoom; camera angle and zoom survive a restart |
| Close window | Quit |

After 22 seconds it pauses automatically. Press R for another take. There are no automatic resets between pushes. The camera follows base translation; mouse interaction is for framing, not adding disturbances in this demo. To record the window on macOS, press **⌘⇧5** and select a recording region.

## Export a ready-to-edit portrait video

Requires `ffmpeg` on PATH, in addition to the simulation environment. Export runs as fast as rendering allows, independent of live-window frame rate:

```sh
.venv-sim/bin/python sim/enclosure_c3/upright/filming_demo.py \
  --record build/filming/c3_force_demo_1080x1920.mp4
```

The result is **1080 × 1920, 9:16, 50 fps, 22 seconds**, H.264 MP4 without audio or UI panels. Orange arrows show the force while it is applied. Use `--no-arrows` for clean footage or `--width 1920 --height 1080` for landscape. The exporter refuses to overwrite an existing video; choose another filename for a new take. A JSON sidecar records controller/model hashes, push vectors and recovery measurements. Videos stay in ignored `build/`, outside Git.

## What the pushes do

| Time from start | World-frame force (N) | Duration |
|---|---|---|
| 3 s | (+0.4, 0, 0) | 0.30 s |
| 9 s | (−0.4, 0, 0) | 0.30 s |
| 15 s | (0, +0.4, 0) | 0.30 s |

Forces act at the **upper link's center of mass**. They are genuine external forces integrated by MuJoCo, not pose changes or pre-recorded joint trajectories. Fixed nominal mechanics and seed 17 make takes repeatable. The sequence is a selected demonstration, not a randomized evaluation or a physical success-rate measurement. Label the footage as simulation.

The [sequence definition](../sim/enclosure_c3/upright/filming_demo.py) contains the timing/vectors. After changing them, check that they still cause falls and leave time for recovery:

```sh
.venv-sim/bin/python sim/enclosure_c3/upright/filming_demo.py --check
```

The check compares two complete takes, including a restart during an active push. It compares physical positions/velocities, commanded targets, observer output and retry count. It also requires all three pushes to cause >60° base tilt and subsequent stable upright/straight recovery, no remaining force after reset/completion, and a final recovered pose. [Recorded validation](../sim/enclosure_c3/upright/filming_demo_validation.json).

[Free mouse-force playground](../sim/README.md) · [Current controller and training results](../sim/enclosure_c3/upright/README.md) · [All documentation](README.md)
