# V1 project summary and video facts

Recorded 7 November 2026. V1 is wrapped as a working experimental self-righting robot. This page separates demonstrated behavior from offline experiments and future ideas.

## What we built

A 3D-printed arm with two perpendicular serial joints on a free-standing base. Two PTK 7465 MG PWM servos, one 500 mAh 1S LiPo and a XIAO nRF52840 Sense carry the controller onboard. The XIAO supplies the single base IMU, battery-voltage measurement and USB charging. One Pololu 2810 serves as the manual battery master switch. No Raspberry Pi, external IMU, separate servo controller or boost converter is used.

The user's final Onshape assembly supplied the arm geometry. A custom under-base cup contains battery, controller, switch and wiring, with accessible USB and slider. Latest CAD is C3; C2 passed the recorded enclosure fit check. C3 tightens the USB aperture and shifts the battery; a separate C3 fit approval is not recorded. Two M2×10 screws attach the enclosure lid.

[CAD/layout](../cad/electronics_pod/README.md) · [BOM](../BOM.md) · [wiring](../electrical/FROM_SCRATCH.md).

## How the controller learned

1. Exported the final assembly, mapped the two hinge axes and grouped components into three rigid bodies.
2. Built a floating-base MuJoCo model with floor contact, component mass/inertia estimates and finite-speed, torque-limited servo dynamics.
3. Searched recovery waypoint sequences and collected successful demonstrations with parameter/noise variations.
4. Behavior-cloned a small neural actor, then compared PPO refinement using Stable-Baselines3. The retained original actor was the stronger behavior-cloning checkpoint.
5. Exported the actor to portable C, calibrated IMU alignment and visual PWM angle signs, checked MCU/host inference agreement, then tested physical recovery.

The deployed original experiment used **71 demonstrations / 13,750 observation-action pairs** and **3,000 behavior-cloning minibatch updates**. PPO refinement ran **67,584 transitions**; it did not improve the retained checkpoint. These are transitions and optimizer updates, not episode counts. [Original experiment, evaluations and checkpoints](../sim/recovery/README.md).

The actor has **4,994 parameters**, about **20 kB of float32 weights**, with 10 inputs and two outputs. It runs at **50 Hz**, with roughly **1.2 ms inference** in recorded hardware checks. Inputs are estimated base gravity direction, angular rate, previous commanded targets and previous actions. The three-wire servos do not report position; actual joint angle and floor contact can be used for simulation rewards but are not policy inputs.

## Demonstrated results

| Observation | Evidence |
|---|---|
| Unassisted physical recovery from sideways, with additional manual disturbances | [2 November trial and operator confirmation](../firmware/policy_control/README.md#first-confirmed-physical-self-righting--2-november-2026) |
| Recovery on battery after unplugging USB | [Standalone deployment record](../firmware/policy_control/results/2026-11-02/standalone_0_2/deployment.json) |
| Both joints responded normally after D8/D7 reroute | [Controller 0.4 deployment](../firmware/policy_control/results/2026-11-07/deployment_0_4.json) |
| Real-board one-minute inactivity latch, motion-command refusals and charge-mode availability | [Controller 0.5 no-PWM capture](../firmware/policy_control/results/2026-11-07/inactivity_0_5.json) |
| Controller 0.6 battery-only automatic startup | Actual-sketch host tests cover start, USB inhibition, faults and inactivity; see [current deployment record](../firmware/policy_control/results/2026-11-07/deployment_0_6.json) for hardware observations |

The recorded sideways run included disturbances, so it is not a clean untouched single-recovery timing measurement. No repeated physical trial count establishes an all-direction success rate.

## Separate enclosure experiment

The later **C2** model relocates electronics/IMU, uses sliced enclosure masses and enables genuine adjacent-link contacts with selective pivot-interface masks. Three PPO experiments ran **202,752 transitions total**. The selected offline candidate achieved **18/30** fresh randomized recoveries versus **8/30** for the original actor on those same new-model cases. It has not replaced the deployed actor.

On a different, familiar 20-case diagnostic, the candidate recovered in **16/20** by 10 seconds and still 16/20 by 60 seconds. That score is neither the fresh 30-case result nor a hardware rate. The original actor's historical **100/100** simulated score belongs to its earlier model/test suite. [Enclosure results](../sim/enclosure/README.md).

Original/deployed-model adjacent-body contact exclusions remain a modeling limitation; the C2 correction is an offline improvement. C3 CAD is not the C2 simulator. Preserve those distinctions when showing a simulation next to real footage.

## Using it on camera

Show a battery-only OFF → ON startup, a sideways recovery, repeated gentle disturbances, the simulation mouse-force playground and the compact electronics layout. A still-base minute followed by refused movement demonstrates the inactivity lock. Use normal battery-only power cycling to wake it; USB-at-startup selects PWM-off charging. [Operating instructions](OPERATING_INSTRUCTIONS.md).

Useful figures already in the repo: [neural recovery animation](../sim/recovery/results/neural_recovery.gif), [searched motions](../sim/recovery/results/searched_recovery.gif), [first physical trial plot](../firmware/policy_control/results/2026-11-02/live_sideways_01.png), [enclosure preview](../cad/electronics_pod/preview.png). A recording of a fresh physical demonstration will be more useful than presenting a simulated score as hardware reliability.

## Future ideas, outside the V1 wrap-up

An integrated MCU/IMU/charger/power PCB to remove wires; onboard RGB battery indication; stronger persistent recovery and expressive behavior; physical servo-dynamics and charging-current characterization; and a C3-matched training model. See the [hardware backlog](HARDWARE_BACKLOG.md) and [recovery behavior notes](RECOVERY_BEHAVIOR.md).

Known receipt totals cover only part of the purchases. Do not describe the under-$100 design target as a verified delivered build cost. No private order screenshots or personal receipt details are needed for the video.
