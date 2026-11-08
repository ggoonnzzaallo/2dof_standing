# V1 project summary and video facts

Recorded 7 November 2026. **Controller 0.9** is uploaded and armed with **±90° targets and automatic straight-arm holding on a level base**. Its new simulation goal requires an upright base and straight joints; 48/50 fresh cases qualified within 25 seconds. Physical 0.9 behavior awaits operator confirmation. Earlier scores and demonstrations below are version-specific. [Current model, range calculations and evidence](../sim/enclosure_c3/upright/README.md).

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

The historical original experiment used **71 demonstrations / 13,750 observation-action pairs** and **3,000 behavior-cloning minibatch updates**. PPO refinement ran **67,584 transitions**; it did not improve the retained checkpoint. These are transitions and optimizer updates, not episode counts. [Original experiment, evaluations and checkpoints](../sim/recovery/README.md).

The actor has **4,994 parameters**, about **20 kB of float32 weights**, with 10 inputs and two outputs. It runs at **50 Hz**, with roughly **1.2 ms inference** in recorded hardware checks. Inputs are estimated base gravity direction, angular rate, previous commanded targets and previous actions. The three-wire servos do not report position; actual joint angle and floor contact can be used for simulation rewards but are not policy inputs.

The historical **0.7 C3** actor warm-starts from the C2 candidate and uses PPO with the firmware IMU filter on the installed geometry. Training completed **202,752 additional transitions / 206 episodes**, with seven saved checkpoints. The checkpoint at **33,792 transitions / 34 completed episodes** was selected on 20 development cases. Held-out simulation recovered a stable base in **49/50 within 15 seconds**, versus **36/50** for the original actor on matched cases. Strict straight-arm success was **0/50**: the reward permits a bent resting arm. These scores do not establish hardware reliability. [C3 records](../sim/enclosure_c3/README.md).

The historical **0.8 robust C3** actor adds 6 g provisional wire/glue mass, broader mechanics variation, a 3 → 5 rad/s target-rate cap and a portable varied-retry supervisor. The deployed checkpoint has **33,792 new PPO transitions / 336 completed episodes**. Saved training reaches 67,584 transitions / 751 episodes; later weights remain offline. On 40 matched genuine fallen held-out cases, corrected 0.8 recovered **40/40 within five seconds**, versus **38/40 within 25 seconds** for 0.7. Failure-capped mean time fell from **3.16 s to 1.76 s**. This is simulation only. [Records, runtime and withdrawn invalid early stage](../sim/enclosure_c3/robust/README.md).

Current 0.9 expands targets to ±90°, uses a gyro-qualified averaged-accelerometer level detector, and eases targets to neutral while level. The selected refinement has **33,792 additional PPO steps / 239 completed episodes**. No substantial self-contact appeared in a 32,761-pose ±90° sweep or eight nominal dynamic recoveries. Lower-joint ±110° intersects the base; upper ±110° clears the sampled structural envelope but has not been physically calibrated.

The retry supervisor remembers stalled attempts and varies sweep order, signs, amplitude and timing. **It is not online learning on the robot.** Battery, sensor, timing and inactivity stops are retained.

## Demonstrated results

| Observation | Evidence |
|---|---|
| Unassisted physical recovery from sideways, with additional manual disturbances | [2 November trial and operator confirmation](../firmware/policy_control/README.md#first-confirmed-physical-self-righting--2-november-2026) |
| Recovery on battery after unplugging USB | [Standalone deployment record](../firmware/policy_control/results/2026-11-02/standalone_0_2/deployment.json) |
| Both joints responded normally after D8/D7 reroute | [Controller 0.4 deployment](../firmware/policy_control/results/2026-11-07/deployment_0_4.json) |
| Real-board one-minute inactivity latch, motion-command refusals and charge-mode availability | [Controller 0.5 no-PWM capture](../firmware/policy_control/results/2026-11-07/inactivity_0_5.json) |
| Controller 0.6 battery-only automatic startup | User-confirmed; [record](../firmware/policy_control/results/2026-11-07/deployment_0_6.json) |
| Controller 0.7 C3 actor uploaded and armed | User subsequently reports physical self-righting failures. [Record](../firmware/policy_control/results/2026-11-07/deployment_0_7.json) |
| Controller 0.9 uploaded and armed | Actor/model/runtime identity and standalone handoff confirmed; physical upright behavior pending. [Record](../firmware/policy_control/results/2026-11-07/deployment_0_9.json) |
| Corrected controller 0.8 uploaded and armed | Actor identity and standalone handoff confirmed; physical recovery awaiting observation. [Record](../firmware/policy_control/results/2026-11-07/deployment_0_8.json) |

The recorded sideways run included disturbances, so it is not a clean untouched single-recovery timing measurement. No repeated physical trial count establishes an all-direction success rate.

## Separate enclosure experiment

The later **C2** model relocates electronics/IMU, uses sliced enclosure masses and enables genuine adjacent-link contacts with selective pivot-interface masks. Three PPO experiments ran **202,752 transitions total**. The selected offline candidate achieved **18/30** fresh randomized recoveries versus **8/30** for the original actor on those same new-model cases. Its selected checkpoint supplied the warm start for the current C3 PPO run; C2 weights themselves were not deployed.

On a different, familiar 20-case diagnostic, the candidate recovered in **16/20** by 10 seconds and still 16/20 by 60 seconds. That score is neither the fresh 30-case result nor a hardware rate. The original actor's historical **100/100** simulated score belongs to its earlier model/test suite. [Enclosure results](../sim/enclosure/README.md).

The original model suppressed adjacent-body contacts. Both C2 and the current C3 model correct this with selective pivot-interface masks. C3 has separate frozen assets, evaluations and actor weights; preserve model/revision distinctions in video footage.

## Using it on camera

Show a battery-only OFF → ON startup, a sideways recovery, repeated gentle disturbances, the simulation mouse-force playground and the compact electronics layout. A still-base minute followed by refused movement demonstrates the inactivity lock. Use normal battery-only power cycling to wake it; USB-at-startup selects PWM-off charging. [Operating instructions](OPERATING_INSTRUCTIONS.md).

Useful figures already in the repo: [neural recovery animation](../sim/recovery/results/neural_recovery.gif), [searched motions](../sim/recovery/results/searched_recovery.gif), [first physical trial plot](../firmware/policy_control/results/2026-11-02/live_sideways_01.png), [enclosure preview](../cad/electronics_pod/preview.png). A recording of a fresh physical demonstration will be more useful than presenting a simulated score as hardware reliability.

## Future ideas, outside the V1 wrap-up

An integrated MCU/IMU/charger/power PCB to remove wires; onboard RGB battery indication; stronger persistent recovery and expressive behavior; physical servo-dynamics and charging-current characterization; and further C3 physical validation/refinement. See the [hardware backlog](HARDWARE_BACKLOG.md) and [recovery behavior notes](RECOVERY_BEHAVIOR.md).

Known receipt totals cover only part of the purchases. Do not describe the under-$100 design target as a verified delivered build cost. No private order screenshots or personal receipt details are needed for the video.
