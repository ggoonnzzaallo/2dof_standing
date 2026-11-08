# Recovery behavior: persistent, with room for personality

User direction, 3 November 2026: a recovery may take several attempts. Occasional misses and expressive physical motion are welcome; permanently getting stuck or abandoning recovery is not. Reliability should mean persistent eventual recovery, not a compulsory perfect first attempt. This is a design target, not a property established by the current actor.

## What the existing scores measure

The enclosure candidate's **16/20** is seven nominal plus nine development cases completing a strict goal within ten seconds. The base must be within 10° of upright, touching the floor, with angular speed below 0.4 rad/s; both joints must be within 0.18 rad (10.3°) of neutral. All conditions must hold for 50 consecutive 50 Hz steps, or one second. Timing starts after sensor initialization and 0.8 s free settling. These are simulated truth checks, not extra sensors available to the actor.

The ten-second horizon is a training/evaluation cutoff. A miss is not proof the robot never got upright, stopped moving, or could not recover with more time. The native playground and battery-powered standalone firmware do not stop at that episode boundary or at success: the policy keeps running until the operator stops it, the 0.5+ firmware inactivity lock triggers, or a genuine sensor, voltage, timing or numerical fault requires stopping. Such faults must stay separate from behavioral retries; automatic fault rearming is not part of this request.

Preserve the original strict scores. Add a **base-only stable recovery** measurement with the same tilt/contact/angular-rate/dwell thresholds but no requirement for straight joints. Report both at 10, 30 and 60 seconds, time to first recovery, unresolved cases and faults. A finite test can establish recovery within its window, not a guarantee of "eventually". On the robot, base tilt/rotation are observable with the IMU; actual joint angles and floor contact remain unmeasured.

`sim/enclosure/evaluate_persistence.py` runs the unchanged deterministic actor beyond the old boundary without teleports, resetting joint-command history, inserting a scripted kick or adding random exploration. It distinguishes too-short evaluation from an actor that remains trapped. These familiar nominal/development cases are diagnostics; new held-out starts and repeated physical disturbances are still needed for a general reliability claim.

**Diagnostic result:** both goals score 16/20 by 10, 30 and 60 seconds. None of the four strict failures becomes a success just by relaxing joint posture or waiting longer. No filter/numerical faults occurred. Those unresolved starts need better recovery behavior, not a relabeling of results. [Raw evaluation](../sim/enclosure/results/persistence_evaluation.json).

## Optional next-iteration training experiment

1. Extend continuous training episodes toward 30–60 seconds. Train through failed attempts, ordinary stumbles and post-recovery disturbances. Use time-limit truncation with bootstrapping; do not treat a missed ten-second deadline as an absorbing "give up" state. Sample starts with varied joint poses and states harvested from failed recoveries, rather than resetting every failure to straight joints.
2. Make stable base recovery the primary goal. Keep a soft preference for a relaxed neutral arm, rather than requiring perfectly straight joints to count a recovery. Continue training after first recovery so the actor learns to stand, react and recover again.
3. Reward progress and time upright, with a carefully bounded dwell/event bonus. Avoid rewarding staying nearly upright forever instead of completing recovery. Do not add a bonus for commanded motion or a fixed repeating wiggle: it can be earned while accomplishing nothing. Tune the discount and horizon together, and compare the actual discounted returns of finishing, loitering and repeating a failed cycle.
4. Penalize excessive action changes, impacts and simulated motor effort modestly. Excessive effort penalties can make lying still preferable to another try. Validate the tradeoff with quiet-standing and persistent-fallen rollouts, not just aggregate reward. Keep physical joint/torque limits and active nonmating contacts.
5. If recurrent failures are trapped deterministic cycles, first improve state coverage and recovery demonstrations. Then compare an escape-capable controller with memory or a small bounded stall-recovery state, including its observation/export cost on the XIAO. Blindly executing the same actor for longer is not a guaranteed escape strategy. No unsupervised hardware exploration is implied.

## Personality without undermining recovery

The desired character is determined and a little imperfect. The printed proportions, inertia, rounded ground-contact edges and compliant motion already affect how recoveries look. Preserve interesting near-misses when they still lead to recovery. If desired later, compare styles such as deliberate rocking versus quick scrambles using a style input or mild style rewards, while holding the same recovery and effort tests. Avoid injecting arbitrary noise just to manufacture mistakes. Mechanical or inertia changes must be reflected in the simulation.

Judge a candidate on recovery by each time threshold, recovery-time distribution, repeated disturbances without controller resets, quiet stable dwell, impact/effort and sensor faults. Show failed trials as well as successful ones. Keep the historical strict score as a secondary regression measure; do not silently relabel old failures as successes.

[Enclosure model and results](../sim/enclosure/README.md) · [Current complete wiring](../electrical/FROM_SCRATCH.md)


## Implemented in controller 0.8 — 7 November 2026

The [robust C3 experiment](../sim/enclosure_c3/robust/README.md) reduces effort penalties, favors prompt recovery, uses heavier/variable-friction/weak-servo models and increases the target-rate cap to 5 rad/s. A portable stateful supervisor replaces repeating deterministic failures with eight bounded large-sweep patterns after stalled progress. It varies order, signs, timing and amplitude. This is scripted retry memory around a learned policy, not online learning. The same header runs in simulation and firmware. Genuine sensor/battery/timing faults and the user-requested one-minute inactivity latch still stop motion. Corrected 0.8 is uploaded/armed; physical effectiveness remains unconfirmed. The invalid early mass-reset stage is explicitly withdrawn in its records.
