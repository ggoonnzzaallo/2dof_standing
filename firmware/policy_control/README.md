# Supervised learned controller 0.1 — trained ±80° targets

This program runs the existing exported actor on the XIAO and can send its outputs to both servos. **Boot is disarmed.** It requires explicit arming, a one-second nominal-neutral hold, and a `run` command. The first deployment is USB-supervised; a host heartbeat is required. It does not yet provide battery-only autonomous arming.

The user explicitly chose the trained **±80°** targets rather than restricting the policy to the measured ±45° range. The actor weights, observation normalization, **50 Hz** update rate and **0.06 radian incremental actions** are unchanged. There is no extra slow calibration slew limiter in the learned-control path: the training servo model already permits finite tracking speed/lag.

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

**This command moves the robot.** The actor runs on the XIAO; the Mac sends heartbeat/stop and records telemetry. It does not choose actions. Ctrl+C requests immediate PWM stop. The host never automatically rearms after a fault. It ends the requested trial after 1–45 seconds and requests OFF; firmware has an independent 60-second run limit. An arm that does not transition to run expires after ten seconds. Stopped PWM does not disconnect the direct servo supply or idle drain; disconnect battery and USB for full OFF/storage.

The serial interface also accepts `arm`, `run`, `shadow`, `keep`, `off`, `!`, `status`, `help` at 115200 baud. `status`/`help` disarm before printing. `keep` only refreshes an already active session. Neither a reconnect nor an unknown command starts control. Do not open another serial monitor during a trial.

## Timing, sensors and fault behavior

The controller reuses the verified LSM6DS3TR-C transport, provisional sensor-to-CAD rotation, recorded gyro bias and portable gravity-direction filter. A dedicated polled 1 MHz TIMER4 counter schedules policy deadlines; the core's micros/DWT configuration is unchanged. Each tick uses DOWN, gyro/10, commanded target/80°, previous action, then clips the actor action to ±1 and integrates exactly 0.06 radians per tick within ±80°. Both hardware pulse widths are validated before either servo is updated.

PWM is detached on stale/invalid IMU data (20 ms), USB disconnect, missing heartbeat (3 s), policy deadline lateness ≥10 ms, invalid numerical state, failed PWM attachment, time limit, input error or explicit stop. Arming requires an estimated BAT node between 3.7 and 4.4 V. While armed/running, ADC sampling every 100 ms stops on two readings below 3.6 V, one below 3.4 V or one above 4.4 V. This retains the prior approximate voltage guard and 100 mA charge selection; it does not measure current, fast brownout transients or net charging. USB-only BAT data with the cell absent is not cell voltage.

Telemetry rows are built into a fixed 256-byte integer-text buffer and written only when the USB FIFO has enough free space. A row is dropped rather than blocking control for host logging. The actor still evaluates at every policy tick. `dropped` records telemetry loss; if the host receives no rows for 500 ms it stops the trial. Fields ending `_u6` encode their dimensionless value multiplied by 1,000,000; `_urad` encodes target radians multiplied by 1,000,000. Pulse values are commanded PWM, not measured shaft positions. The host handles skipped-frame history checks and permits quantization error in numerical comparisons.

Offline inspection sends no device commands:

```sh
.tools/arduino/python/bin/python scripts/control.py --shadow --analyze build/control/shadow_01.csv
.tools/arduino/python/bin/python scripts/control.py --analyze build/control/upright_01.csv
```

## Evidence and remaining model limitations

Native build: **84,600 bytes flash / 7,880 bytes static RAM**, Seeed nRF52 1.1.13, native Arm GNU 13.2.Rel1, `-O2`. The uploader acknowledged `Device programmed.` on 2 November 2026. Actual-sketch host tests cover the real actor, ±80°/789–2211 µs mapping, arming/hold, target integration, shadow isolation, startup, PWM attachment failures, battery/sensor/non-finite/USB/heartbeat/deadline/session/input stops, nonblocking telemetry at maximum row size and timer rollover. The actual test sketch's telemetry also passes through the host recorder's actor/history/integration/PWM checks. The existing firmware regression suite passes.

The user identified broad adjacent-body collision exclusions as a training-model flaw. They originally avoided artificial contact forces at fitted pivot/housing interfaces but also suppress genuine clashes. **The current model excludes base–middle and middle–upper contact.** Recorded-trajectory screening does not prove full-range physical clearance. At the user's request, correction is [required for the next training pass](../../docs/SIM_CALIBRATION_PLAN.md#required-correction-at-the-next-training-pass--2-november-2026), then demonstrations/training/evaluation must be revisited. The current policy/XML are intentionally unchanged for this deployment.

The filtered-observation simulation result is 26/30 fresh trials, versus 30/30 on the same seeds with exact DOWN. Physical travel, compound clearance, actual servo dynamics and estimator accuracy under impacts remain unverified. The current deployment uses explicitly recorded assumptions; a completed software check or emitted PWM command is not a demonstrated physical recovery.


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

This does not establish all-direction recovery, repeated-trial reliability, full compound clearance, low-battery operation or untethered autonomy. The present firmware deliberately requires USB heartbeat and boots disarmed. Battery-only arming/stop behavior is a separate next implementation step. The collision-model correction remains required before the next training run.
