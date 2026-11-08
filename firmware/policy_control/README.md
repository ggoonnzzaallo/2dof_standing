# Learned controller — trained ±80° targets

**Current source: 0.8, 7 November 2026. Lower servo PWM is D8 / printed 8; upper is D7 / printed 7.** This matches the user's new harness. Startup, stop, charge and fault paths drive those same pins LOW; D2 remains unused. The status banner reports the pin assignment. Bench, calibration and sensor-only sketch sources also follow D8/D7. Pin movement changes neither the actor weights, joint order, pulse-to-angle calibration nor training model.

**Uploaded and armed 7 November 2026:** controller **0.8** uses the corrected-pose **robust C3 PPO actor**, a **0.10 rad/tick (5 rad/s) target-rate cap**, and varied stalled-recovery sweeps. The previous 0.7 actor failed to self-right the physical C3 build. Corrected 0.8 physical recovery is awaiting operator observation. [Deployment record](results/2026-11-07/deployment_0_8.json) · [training, runtime and limits](../../sim/enclosure_c3/robust/README.md).

The [manifest](PolicyManifest.json) pins actor, model, training report and runtime-source hashes. Builds check them; live arming checks version, geometry and actor identity. Battery-only startup, USB-at-startup charging and the reboot-only one-minute inactivity latch are retained. [Operating instructions](../../docs/OPERATING_INSTRUCTIONS.md). Stop/status remain available for older firmware. Version-specific evidence below is historical.

This program runs the selected robust C3 exported actor on the XIAO and can send its outputs to both servos. **Battery-only boot automatically arms and starts standalone recovery; USB-at-boot selects CHARGE with PWM off.** Explicit Mac arming remains available for bench work. Every motion start still requires fresh sensors, valid voltage and a one-second nominal-neutral hold. Version 0.3 introduced latched no-PWM charging, included in 0.4 and later; actual charging acceptance remains pending. Version 0.2 supports explicit Mac arming followed by USB-free operation; see [standalone operation](#standalone-operation-02--arm-from-the-mac). Supervised trials still require a host heartbeat.

The user explicitly chose the trained **±80°** targets rather than restricting the policy to the measured ±45° range. Controller 0.8 changes the actor weights and increases incremental actions to **0.10 radian per tick**; the observation contract and **50 Hz** update rate remain unchanged. There is no extra slow calibration slew limiter in the learned-control path: the training servo model already permits finite tracking speed/lag.

Both visually measured PWM signs are negative. The deployment profile uses `pulse_us = 1500 - 509.295817894 * angle_rad`, giving approximately **789–2211 µs** over ±80°. This linearly extrapolates the [measured 0°/±45° references](../servo_calibration/results/2026-11-02/visual_mapping.json); it is not an additional angle or end-stop measurement. The original offline measurement converter still refuses extrapolation. `ServoProfile.h` is the separately authorized deployment profile.

## Upload and no-motion check

Unplug the battery and both complete three-pin servo plugs, connect USB, and leave the base still while the gravity filter initializes.

```sh
python3 scripts/robot.py build-control
python3 scripts/robot.py upload-control
.tools/arduino/python/bin/python scripts/control.py --shadow --seconds 10 --out build/control/shadow_01.json
```

Shadow mode runs the same sensor filter, actor and target integration without attaching either PWM output. Its PWM fields must remain zero. The recorder verifies the complete ready/disarmed firmware banner, keeps the USB session alive, records CSV and raw text, checks actor/host agreement and integration afterward, and sends an explicit stop. Use a new output filename each time.

## Live supervised trial

With USB unplugged, reconnect both servo plugs and the battery, then reconnect USB. Start with the robot upright and both joints near straight on a clear surface, with USB cable slack and room for the trained range. Be present to stop/catch it if needed. Both joints are commanded to 1500 µs during arming; the servos expose no angle feedback to make that initial acquisition position-aware.

```sh
.tools/arduino/python/bin/python scripts/control.py --seconds 15 --out build/control/upright_01.json
```

**This command moves the robot.** The actor runs on the XIAO; the Mac sends heartbeat/stop and records telemetry. It does not choose actions. Ctrl+C requests immediate PWM stop. The host never automatically rearms after a fault. It ends the requested trial after 1–45 seconds and requests OFF; firmware has an independent 60-second run limit. An arm that does not transition to run expires after ten seconds. Stopped PWM does not disconnect the servo supply or idle drain; unplug USB and slide the Rev C switch OFF for storage.

The serial interface also accepts `arm`, `run`, `shadow`, `keep`, `off`, `!`, `status`, `help` at 115200 baud. `status`/`help` disarm before printing except in CHARGE/INACTIVE, where they preserve the latched state. `state` is the non-stopping read used by `./robot status`. `keep` only refreshes an already active session. Neither a reconnect nor an unknown command starts control. Do not open another serial monitor during a trial.

## Timing, sensors and fault behavior

The controller reuses the verified LSM6DS3TR-C transport, provisional sensor-to-CAD rotation, recorded gyro bias and portable gravity-direction filter. A dedicated polled 1 MHz TIMER4 counter schedules policy deadlines; the core's micros/DWT configuration is unchanged. Each tick uses DOWN, gyro/10, commanded target/80°, previous action, then clips the action to ±1 and integrates up to **0.10 radians per tick within ±80°**. When stalled, the portable retry supervisor can replace the actor action before that same bounded integration. Both hardware pulse widths are validated before either servo is updated.

PWM is detached on stale/invalid IMU data (20 ms), policy deadline lateness ≥10 ms, invalid numerical state, failed PWM attachment, input error or explicit stop. Supervised modes additionally stop on USB disconnect, missing heartbeat (3 s) or their time limit; explicit standalone mode continues without USB or heartbeat. Arming requires an estimated BAT node between 3.7 and 4.4 V. While armed/running, ADC sampling every 100 ms stops on two readings below 3.6 V, one below 3.4 V or one above 4.4 V. This retains the prior approximate voltage guard and 100 mA charge selection; it does not measure current, fast brownout transients or net charging. USB-only BAT data with the cell absent is not cell voltage.

Telemetry rows are built into a fixed 256-byte integer-text buffer and written only when the USB FIFO has enough free space. A row is dropped rather than blocking control for host logging. The actor still evaluates at every policy tick. `dropped` records telemetry loss; if the host receives no rows for 500 ms it stops the trial. Fields ending `_u6` encode their dimensionless value multiplied by 1,000,000; `_urad` encodes target radians multiplied by 1,000,000. Pulse values are commanded PWM, not measured shaft positions. The host handles skipped-frame history checks and permits quantization error in numerical comparisons.

Offline inspection sends no device commands:

```sh
.tools/arduino/python/bin/python scripts/control.py --shadow --analyze build/control/shadow_01.csv
.tools/arduino/python/bin/python scripts/control.py --analyze build/control/upright_01.csv
```

## Evidence and remaining model limitations

Historical 0.1 native build: **84,600 bytes flash / 7,880 bytes static RAM**, Seeed nRF52 1.1.13, native Arm GNU 13.2.Rel1, `-O2`. The uploader acknowledged `Device programmed.` on 2 November 2026. Actual-sketch host tests cover the real actor, ±80°/789–2211 µs mapping, arming/hold, target integration, shadow isolation, startup, PWM attachment failures, battery/sensor/non-finite/USB/heartbeat/deadline/session/input stops, nonblocking telemetry at maximum row size and timer rollover. The actual test sketch's telemetry also passes through the host recorder's actor/history/integration/PWM checks. The existing firmware regression suite passes.

The original model excluded base–middle and middle–upper contacts. The C3 and current [robust C3 model](../../sim/enclosure_c3/robust/README.md) enable genuine adjacent-body contact, masking only small pieces at fitted pivot interfaces. Old simulation and hardware metrics below refer to their original model/actor revisions.

The historical 0.7 C3 PPO actor achieved **49/50 stable-base recoveries** within 15 seconds on held-out simulated cases versus **36/50** for the original actor on matched cases. Strict straight-arm success was **0/50**: its relaxed reward permits a bent resting arm. Cup mass is a provisional volume-scaled slicer estimate; servo dynamics, friction and impact estimation remain imperfectly characterized. Software results and an arming acknowledgement do not establish physical C3 recovery.


## First hardware shadow check — 2 November 2026

The user confirmed USB-only power with battery and both complete servo plugs disconnected. Upload acknowledged `Device programmed.`. The ten-second no-PWM check captured **500/500 policy frames**, zero I2C errors, zero dropped rows and zero PWM outputs. Actor inference was **1,217 µs median / 1,225 µs maximum**; maximum deadline lateness **1,382 µs**, maximum sample age **5,169 µs**. Logged integer observations agreed with host C inference within **1.29e-6** action units; target/history/unit-DOWN checks passed. The host received an explicit emergency-OFF acknowledgement. Virtual targets reached 17.5°; this was a software check, not a physical response.

[Raw evidence](results/2026-11-02/shadow_01.json) and [source/image provenance](results/2026-11-02/deployment.json) are preserved. Live PWM trials are a separate stage.


## First live upright trial — 2 November 2026

With the user's confirmed battery/servo connections and upright clear setup, the host armed both joints and ran the unchanged actor for 15 seconds. **750 frames** completed, with **zero I2C errors or dropped rows**, 1,218 µs median / 1,225 µs maximum inference and 1,379 µs maximum deadline lateness. Numerical action/history/integration/PWM checks passed; an explicit OFF was acknowledged. USB-connected BAT estimates were **4.126–4.147 V**. The allowed range was ±80°; the largest actual commanded target in this trial was **18.48°**, not a full-range excursion.

The user confirmed: **moved freely and stayed standing**, without reported clashes or sustained buzzing. [Raw telemetry and report](results/2026-11-02/live_upright_01.json) are preserved. This confirms a first upright control-loop trial, not recovery from a fall or full-range physical clearance.


## First confirmed physical self-righting — 2 November 2026

The user placed the whole robot sideways with its base vertical and lower horn side up, and watched the next 15-second trial. The policy used its full ±80° target limits, reaching commanded pulses **789 and 2211 µs**. All **750 frames** completed, with zero I2C errors/dropped telemetry, **1,230 µs median / 1,272 µs maximum inference**, and **1,378 µs** maximum deadline lateness. BAT estimates with USB were **4.123–4.150 V**. Numerical actor/history/integration/PWM checks passed, and OFF was acknowledged.

Estimated base tilt began at **98.6°** and ended at **1.52°**. The user explicitly confirmed **recovery without assistance**, and confirmed additional manual disturbances/repositions during the run. Exact disturbance times and count were not recorded, so the trace must not be labeled an untouched single recovery trajectory or used to claim a success rate. This is our first user-observed physical self-righting result.

![Estimated base tilt, commanded angles and battery estimate during the first sideways trial](results/2026-11-02/live_sideways_01.png)

[Raw logs](results/2026-11-02/live_sideways_01.json) and [operator observations](results/2026-11-02/sideways_observation.json) are preserved. Recreate the figure with `.venv-sim/bin/python scripts/plot_control.py firmware/policy_control/results/2026-11-02/live_sideways_01.csv --out build/control/sideways.png`. The figure shows estimated base orientation and commanded joint targets; no actual shaft angles are measured.

This does not establish all-direction recovery, repeated-trial reliability, full compound clearance, low-battery operation or untethered autonomy. That first 0.1 firmware required USB heartbeat and booted disarmed. Version 0.2 adds explicit standalone arming while retaining disarmed boot; see below. That contact correction has since been implemented in the separate [C2 enclosure experiment](../../sim/enclosure/README.md); controller 0.7 subsequently replaces the original actor with the C3 candidate.

## Standalone operation 0.2 — arm from the Mac

Version 0.2 adds an explicit standalone mode. **Boot and power-cycle remain disarmed.** Connect the battery, servos and USB with the robot near straight and free to move. From the repository folder:

```sh
./robot arm
```

The Mac verifies ready firmware, commands nominal neutral, waits one second, starts the unchanged trained policy and confirms standalone mode with advancing policy frames. After **“Armed. Unplug USB”**, close the terminal or unplug USB: control continues on the XIAO. No Mac heartbeat or fixed 60-second trial limit applies in standalone mode. Firmware 0.5+ adds a separate 60-second base-IMU inactivity stop; 0.6 adds automatic battery-only boot. Reset does not restore a previous command history.

```sh
./robot status
./robot stop
```

`status` reads a short state packet without stopping/recentering a running standalone controller. Reconnect USB first if needed. `stop` requests and verifies PWM OFF; it works even if the IMU is not ready. For Rev C full OFF, unplug USB and slide OFF. A low-battery fault stops PWM but cannot disconnect servo idle drain, so isolate battery power after use or a fault.

These commands are also available in VS Code **Tasks → Run Task → Robot: arm for untethered use / stop PWM / read state without stopping**. The executable uses the project's Python environment, so no activation or Arduino IDE is needed. It logs command confirmations under `build/arming/`. If the firmware refuses arming or the handoff fails, the helper requests stop; only a positively confirmed handoff omits the usual cleanup stop.

Standalone retains the same ±80° range, 50 Hz policy, action increments, PWM mapping, sensor-age/finite-state checks, ≥10 ms late-deadline stop and battery thresholds. Those checks continue while USB is absent. A sensor/battery/timing fault stops and stays stopped; reconnecting USB cannot automatically rearm. The normal `scripts/control.py` supervised trials and no-PWM shadow mode keep their original heartbeat and duration limits. The raw serial `status`/`help` commands still stop active motion before printing the full banner (0.3 preserves already-latched charging mode); `./robot status` instead uses the new non-stopping `state` command.

Firmware tests cover more than a simulated minute of standalone inference with USB disconnected, heartbeat/normal-trial expiry ignored only in standalone, reconnect/history continuity, non-stopping state, explicit stop and untethered battery/sensor/timing faults. Mac-helper tests cover handoff success without accidental cleanup OFF, failed-handoff stop, non-stopping status, protocol checks, and stopping when the filter is unavailable. Historical 0.1 captures above remain unchanged.

Version 0.2 was built and uploaded on 2 November 2026: **85,300 bytes flash / 7,880 bytes static RAM**. The full firmware regression suite and five Mac-helper tests passed. The first USB-only state check reported **OFF, zero policy frames, “Boot disarmed.”**; the BAT-node reading without a cell is not a battery measurement. Hardware arming confirmed standalone mode at frame 11; a separate status process then confirmed mode 4 at frame 286 without stopping it. The user subsequently confirmed **“Yes—recovers with USB unplugged.”** [Version 0.2 deployment, captures and observation](results/2026-11-02/standalone_0_2/deployment.json) are preserved. This establishes an observed battery-only recovery demonstration, not an all-orientation reliability rate.

## Charging mode (0.3)

Historical 0.3 source stage, **3 November 2026**. This behavior is included in uploaded 0.6; full electrical charging characterization remains unrecorded. No policy weights, PWM calibration or trained target range changed. With the selected [Rev C master-switch harness](../../electrical/README.md), keep the switch **ON** and USB connected, support the arm and run:

```sh
./robot charge
./robot status
```

The helper first stops/acknowledges PWM OFF, then requests `charge` and confirms mode **5**. It sends no arm or servo-motion command. Both PWM channels detach and the selected signal pins go LOW (D0/D1 in 0.3; D8/D7 in 0.4 and later); approximately 100 mA charge configuration remains selected. Charge mode is latched across terminal close, USB/DTR loss/reconnect and status/help/state requests. It requires no heartbeat or healthy IMU. Sensor faults and trial deadlines cannot resume PWM. `run`, `standalone` and `shadow` are refused while charge mode is latched; explicit `arm` acquires neutral again unless the 0.5 inactivity lock is set, in which case reboot is required first. `off`/`!` remain available and also leave PWM off. In historical 0.3, reset booted disarmed. Current 0.8 retains 0.6 behavior and selects automatic recovery without USB or charge mode with USB.

The charger itself operates automatically on USB; mode 5 confirms **PWM inhibition**, not positive battery current or a full cell. Servo power remains present. In Rev C, **USB unplugged + switch OFF** isolates the cell for storage; OFF + USB cannot charge the isolated cell and can still power the shared rail from the charger. There is no switch-position or battery-current sensor. Reverse-path charging, no-PWM servo idle load and charging termination remain unmeasured. C2 enclosure fit passed; separate C3 fit confirmation is not recorded.

Build/upload before closing the new enclosure, initially with battery and complete servo plugs unplugged:

```sh
python3 scripts/robot.py build-control
python3 scripts/robot.py upload-control
```

Native build passed: **85,900 bytes flash / 7,880 bytes static RAM**. The actual-sketch fake-hardware regression passed, including charge entry from active motion, no pulses/frames for over a minute with no USB and stale IMU, retained mode after status/reconnect, refusal of run/standalone/shadow, emergency stop and explicit rearm. **Eight** Mac-helper tests passed, including no-motion charging without a ready filter, serial-close persistence, status preserving charge and old firmware failing stopped. The helper still accepts controller 0.2 for existing arm/stop/status; new charge mode reports that 0.3 is required. No hardware commands were sent during this preparation.


## Signal-pin reroute (0.4) — 7 November 2026

The user wired lower signal to printed 8 and upper to printed 7. Current attach, boot, stop and fault paths use **D8** and **D7**, respectively. The installed Seeed non-mbed core maps these to **P1.13** and **P1.12**; hardware PWM routes through the core pin map. Neither SPI nor Serial1 is used, so the alternate SCK/RX labels do not conflict. USB `Serial` is unchanged. Former D0/D1 are unwired; D2 stays unused.

All maintained motion and sensor-only sketches use the new pins. The bench program retains its existing command protocol; help strings name the current pins. Historic diagrams, measurements and captures keep their original pin assignments. The trained actor, IMU filter, calibration signs, target range and 50 Hz timing are unchanged; this wire reroute needs no model retraining.

At this historical stage the Mac helper required controller 0.4, 0.5 or 0.6 before `arm`, supervised control or `charge`, and rejects old banners before sending motion/charge commands. Charge-version checks do not require a healthy IMU. `stop` and non-stopping `status` remain usable with old firmware.

The native controller build succeeds at **85,940 bytes flash / 7,880 bytes static RAM**. The full regression suite passes, including actual lower/upper pin ordering, disabled D8/D7 after faults/charge, driver PWM on pins 8 and 7, and refusal of old firmware by the Mac helpers. That offline validation preceded the separate hardware deployment below.

[Pin-update build and validation record](results/2026-11-07/pin_routing_0_4.json).

To install, first unplug the battery and both complete three-pin servo plugs, leaving USB connected, then run:

```sh
python3 scripts/robot.py upload-control
```

Upload verification, a no-motion state check and a supervised joint test follow separately; a successful compile is not an uploaded or physically validated pin assignment.


## Hardware deployment 0.4 — 7 November 2026

The user explicitly requested upload with battery and servos still connected. The existing controller acknowledged OFF, the uploader returned **Device programmed.**, and a disarmed status banner confirmed **lower D8 / upper D7** with ready IMU/filter. The three-second no-PWM check captured **150/150 frames**, zero I2C errors and zero dropped rows. Median/max inference were **1,200/1,206 µs**; host action parity error from quantized observations was **1.21e-6**. Both PWM fields stayed zero, and OFF was acknowledged.

At the user's instruction the host then armed, held nominal neutral and entered standalone mode. A later non-stopping status read confirmed mode 4 at frame **1,231**, with sensor readiness, zero I2C errors and BAT-node estimate **4.137 V** while USB was connected. The user confirmed **both joints respond normally without binding or sustained buzzing**. Control was left running as requested; no automatic stop was sent after successful handoff.

This confirms deployment and normal joint response on the new signal pins, not an isolated per-joint angle test, a new all-direction recovery score, or charging/termination validation. The existing deployed actor remains unchanged; the newer enclosure candidate remains offline. [Deployment summary](results/2026-11-07/deployment_0_4.json), [no-PWM check](results/2026-11-07/shadow_0_4.json), [arming](results/2026-11-07/arm_0_4.json), [non-stopping state](results/2026-11-07/status_0_4.json).


## Reboot-only inactivity lock 0.5 — 7 November 2026

`InactivityGuard.h` monitors fresh base-frame acceleration and gyro in RUN, STANDALONE and SHADOW. Each new control run starts a 60,000 ms timer. Three consecutive samples exceeding either 0.08 rad/s gyro norm or 0.04 g acceleration-vector displacement reset it. Acceleration compares against the last accepted motion reference, so a gradual tilt can accumulate; single-sample spikes and below-threshold noise do not reset it. Elapsed-time arithmetic handles 32-bit millisecond rollover.

At expiration, the persistent-in-RAM lock sets **INACTIVE (6)**, detaches both PWM channels and holds D8/D7 LOW. Only MCU reset clears the lock. `arm`, `run`, `standalone` and `shadow` refuse while locked, including after `off`, emergency stop, unknown commands, USB reconnect or CHARGE. No serial command clears it. CHARGE (5), state reads and battery-voltage sampling remain available; charge-mode entry preserves the lock. PWM stop leaves servo supply/idle draw connected and does not establish net battery charging. Boot remains disarmed, with the actor, calibration and existing fault guards unchanged.

Host tests exercise the real sketch through a one-minute stationary standalone run, rejected wake commands, charging after lock, simulated reboot, periodic movement, subthreshold noise, slow tilt, isolated spikes and rollover. Mac helpers recognize mode 6, reject arming without reboot, and permit charge with a locked/unready IMU. They still support 0.4 for the unchanged pin mapping; only 0.5 includes this timeout.


[Hardware timeout capture](results/2026-11-07/inactivity_0_5.json): 2,999 no-PWM frames, timeout at 59.999 host seconds, stationary gyro maximum 0.0129 rad/s, mode 6 and all motion commands refused. Charging mode remained available and USB serial reopening preserved the lock. The controller was left in CHARGE (5) with the inactivity lock set. This verifies the board's guard/command path without driving motors; real-servo vibration and charging current were not measured. [Build/upload evidence](results/2026-11-07/deployment_0_5.json).


## Battery-only automatic startup 0.6 — 7 November 2026

No computer is needed for everyday running. Boot initially holds PWM off. Physical USB VBUS at startup selects CHARGE, independent of USB enumeration, CDC/DTR or host commands; this includes a wall supply. USB removal does not automatically leave charge mode. Without USB, the firmware waits at least two seconds for fresh IMU/filter data, calls the existing guarded neutral-arm routine, holds neutral for one second, then starts STANDALONE. Initialization times out at 15 seconds. Startup voltage limits remain 3.7–4.4 V.

Explicit stop, charge, arm/shadow commands and any startup fault cancel the pending automatic sequence. There is no automatic retry after low voltage, failed PWM attachment or stale sensors. USB arriving during initialization/neutral acquisition stops PWM and selects CHARGE. Once STANDALONE is running, connecting USB retains the existing behavior: it does not automatically stop motion. Use inactivity, an explicit stop/charge command, or a full USB-at-boot charging sequence.

The inactivity lock still requires reset. With USB absent, reboot clears it and automatically starts recovery again; with USB present, reboot clears it into charge mode. Host regression covers both startup paths, physical VBUS independently of serial state, charge persistence on USB removal, startup cancellation/failures, and inactivity followed by reboot. The native build is **87,128 bytes flash / 7,920 bytes static RAM**. [Deployment and hardware observations](results/2026-11-07/deployment_0_6.json).


## C3 policy deployment 0.7 — 7 November 2026

The C3 model freezes the installed thicker enclosure, battery against the wall and translated IMU. The new PPO actor warm-started from the C2 candidate. Full firmware regression and 13 Mac-helper tests passed before deployment; native build is **87,704 bytes flash / 7,920 bytes static RAM**. C export versus SB3 agreed within **3.58e-7** on 1,000 vectors.

The uploader acknowledged **Device programmed.** USB startup selected CHARGE with zero policy frames. The already-completed flat sensor capture reported **2.49°** estimated tilt, ready IMU/filter and no I2C errors; the measured mounting rotation was retained. At the user's request to run without more tests, `./robot arm` acquired neutral, selected STANDALONE and confirmed advancing policy frames at **4.145 V BAT**. The host left control running after closing serial; no follow-up hardware tests or stop were sent.

Firmware prints `POLICY_GEOMETRY: installed_enclosure_c3` and actor header SHA-256 `0857ad97462e121bb45a72f2700950a98bfc391235571acfd3c09ad62948a047`. `PolicySelection.h` includes the selected C3 header; builds verify the actor archive, model, mesh bundle and training-report hashes. Live helpers verify banner identity. The new non-stopping `sensors` read reports fresh DOWN, corrected gyro and base acceleration without attaching PWM or changing modes.

[Deployment and source/image hashes](results/2026-11-07/deployment_0_7.json) · [flat sensor capture](results/2026-11-07/c3_flat_sensors_0_7.json) · [standalone handoff](results/2026-11-07/arm_0_7.json). The user subsequently reported that this 0.7 actor repeats failed physical attempts. Controller 0.8 below supersedes it. Startup, inactivity, voltage and fault behavior remain as documented above.


## Stronger recovery and varied retries 0.8 — 7 November 2026

The corrected robust actor is warm-started from valid 0.7 weights and trained on the heavier C3 model with wider friction, COM, torque, speed and delay variation. The deployed checkpoint has 33,792 additional PPO transitions / 336 completed episodes. A later saved checkpoint at 67,584 transitions / 751 episodes improved the 20-case mean by only 0.035 s; it is retained offline. In 40 matched genuine fallen held-out cases, corrected 0.8 scored 40/40 by five seconds versus 0.7's 38/40 within 25 seconds. These are simulation results. [Full details](../../sim/enclosure_c3/robust/README.md).

`RecoveryStrategy.h` uses base DOWN and command history to recognize stalled attempts, then temporarily commands one of eight cosine-interpolated patterns, varying signs, joint order, timing and 70–80° target amplitude. It returns to policy actions within about 10° of level, requires one full second level before clearing retry memory, and keeps bases stuck 11.5–25° from level eligible for new attempts. It never exceeds ±80° or 0.10 rad/tick, and never bypasses fault/inactivity stops. This adds behavioral memory, not online weight learning. The exact release header also runs in MuJoCo. The post-training level/dwell refinement is separately [validated](../../sim/enclosure_c3/robust/results/runtime_validation.json); the original training header is preserved. Firmware and host handshake include a retry-runtime fingerprint in addition to the actor identity. Telemetry appends a `retry` boolean; actor parity checks apply to non-overridden rows, while target/history/PWM bounds are checked on every row. Historical `--analyze` can specify `--increment .06` and the appropriate `--actor-header`.

An early mass-reset training bug invalidated the first 0.8 candidate and its reported scores; PWM was stopped and the stage marked [invalid](results/2026-11-07/deployment_0_8_early_invalid.json). Corrected code explicitly preserves fallen qpos/qvel across mass updates and tests upright, side, inverted and diagonal reset poses. Retraining starts from the valid 0.7 actor. No invalid weights or scores are used in the corrected deployment claims.

Before corrected upload, the real-sketch/host tests passed, including forced-fallen retries, plus the portable eight-pattern/bounds/timing check, 13 Mac-helper tests and corrected-pose simulation regression. C export versus SB3 max error is 3.58e-7 on 1,000 vectors. Native build is **89,364 bytes flash / 7,968 bytes static RAM**. The uploader acknowledged **Device programmed.** and `./robot arm` confirmed STANDALONE at frame 10 / **4.135 V BAT**. Control was left running after serial closed; no later stop or physical trial was sent. [Deployment and hashes](results/2026-11-07/deployment_0_8.json) · [handoff](results/2026-11-07/arm_0_8.json). Physical C3 recovery with the corrected actor remains unconfirmed.
