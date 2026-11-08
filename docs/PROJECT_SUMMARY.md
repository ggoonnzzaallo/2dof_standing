# Project summary and video facts

Recorded **7 November 2026**. A small, 3D-printed, two-joint robot uses an onboard neural controller to get back upright. Inspired by [Homemade Garbage's project](https://homemadegarbage.com/rl13). [Operating instructions](OPERATING_INSTRUCTIONS.md) · [All documentation](README.md).

## What we built

Two perpendicular serial joints use **PTK 7465 MG PWM servos**. A **XIAO nRF52840 Sense** supplies compute, one base IMU, battery-voltage sensing and USB-C charging. A **500 mAh 1S LiPo** powers the robot through one **Pololu 2810 master switch**; servo signals are D8 lower / D7 upper. There is no Raspberry Pi, external IMU, servo-driver board or boost converter.

The arm comes from the user's final Onshape assembly. A custom under-base enclosure packages the battery, controller, switch and wires, with accessible USB and slider. Latest cup: C3, tighter USB opening and battery against the wall; the C2 lid is unchanged and attaches with two M2×10 screws into plastic. [CAD/layout](../cad/electronics_pod/README.md) · [BOM](../BOM.md) · [Wiring](../electrical/FROM_SCRATCH.md).

## How it learned

1. Export the CAD, map the hinge axes and group components into three rigid bodies.
2. Build a floating-base MuJoCo model with floor contact, mass/inertia estimates and finite-speed, torque-limited servos.
3. Search successful recovery sequences and behavior-clone a small neural actor.
4. Refine with Stable-Baselines3 PPO on the revised enclosure, randomizing friction, mass/COM and servo behavior.
5. Export actor-only C, calibrate IMU alignment and PWM signs, compare MCU/host inference and deploy onboard.

The actor has **10 inputs, two outputs and 4,994 float32 parameters** (~20 kB). It runs at **50 Hz**, with roughly **1.2 ms inference** in recorded hardware checks. It sees base gravity direction, angular rate, commanded targets and previous applied actions. Three-wire servos do not report shaft angles; simulated joint positions/contact support training rewards but are not policy inputs.

**Current controller 0.9** uses ±90° targets, varied retries when progress stalls, and smooth neutral holding when the base is level. The retry supervisor remembers attempts; **it does not learn new neural weights onboard**. Battery-only startup, USB-at-startup charge mode, voltage/sensor stops and reboot-only one-minute inactivity shutdown are retained.

## Results and limits

| Evidence | What it establishes |
|---|---|
| [2 November physical recovery](../firmware/policy_control/HISTORY.md#first-confirmed-physical-self-righting--2-november-2026) | User-observed unassisted recovery with additional disturbances, on the earlier geometry/controller |
| [Battery-only demonstration](../firmware/policy_control/results/2026-11-02/standalone_0_2/deployment.json) | Recovery after unplugging USB |
| [Automatic startup](../firmware/policy_control/results/2026-11-07/deployment_0_6.json) | User-confirmed computer-free startup after a battery power cycle |
| [Current C3 evaluation](../sim/enclosure_c3/upright/README.md) | 48/50 fresh upright-and-straight simulated cases within 25 seconds; five initially bent flat-base checks straightened |
| [Controller 0.9 deployment](../firmware/policy_control/results/2026-11-07/deployment_0_9.json) | Upload and standalone handoff confirmed; physical recovery/straight-hold accuracy await observation |

The selected 0.9 refinement used **33,792 additional PPO transitions / 239 completed episodes**. [Checkpoints and success definition](../sim/enclosure_c3/upright/README.md#training-and-evaluation). Sampled geometry checks support ±90° on both joints; lower ±110° intersects the base. Servo endpoints, loaded dynamics, charging current/termination and some mass values remain unmeasured or estimated.

Earlier simulation scores use different geometry and success criteria. They are not a hardware reliability trend. [Experiment history](../sim/README.md#experiment-history) · [Firmware development records](../firmware/policy_control/HISTORY.md). Receipt coverage is incomplete; under $100 was a design target, not a verified delivered cost.

## Filming ideas

Show battery-only OFF → ON startup, a fresh sideways recovery attempt, gentle disturbances, the mouse-force simulation and compact electronics layout. A still-base minute followed by refused movement demonstrates the inactivity lock; a battery-only power cycle wakes it. USB-at-startup selects PWM-off charging. [Operating instructions](OPERATING_INSTRUCTIONS.md).

Existing visuals: [original neural recovery animation](../sim/recovery/results/neural_recovery.gif), [first physical trial plot](../firmware/policy_control/results/2026-11-02/live_sideways_01.png), [enclosure preview](../cad/electronics_pod/preview.png). Label simulation footage and controller revisions; record current physical behavior before claiming improved real-world performance.

Future ideas: [integrated controller PCB](INTEGRATED_CONTROLLER_PCB.md), [battery LED/hardware backlog](HARDWARE_BACKLOG.md), and [persistent recovery/personality](RECOVERY_BEHAVIOR.md).
