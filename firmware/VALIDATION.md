# Bench firmware validation — 30 October 2026

**Current design update:** Rev B removes the Pololu. Version 0.4 defaults to direct battery power and is prepared in source; the last physically tested/uploaded version remains 0.3 on Rev A. All measurements and motor observations below predate the requested physical rewire. No robot upload or motion command was performed during the Rev B schematic change.

## Passed

- Full target build for `Seeeduino:nrf52:xiaonRF52840Sense` using Arduino CLI 1.5.1, Seeed nRF52 Boards 1.1.13 and native Apple Silicon Arm GNU 13.2.Rel1 / GCC 13.2.1.
- Bundled libraries: Adafruit TinyUSB 1.7.0 and Servo 1.1.2. No separately installed Servo library is used.
- Target sizes: version 0.1 **50,224 bytes flash / 7,704 bytes global RAM**; version 0.2 **50,976 bytes flash / 7,704 bytes global RAM**; version 0.3 **51,184 bytes flash / 7,704 bytes global RAM**.
- Native Arduino ctags 5.8-arduino11 built from official source. The local cached source renames the reserved `__unused__` macro to avoid a collision with current macOS SDK headers. This cache is excluded from git.
- Host tests against the actual sketch: disarmed boot, explicit newline arming, exactly 1500 µs commands, one selected PWM output, timed power-off, serial disconnect shutdown, immediate stop, malformed/overlong input, timer rollover and PWM attachment failure.
- Version 0.2 host tests additionally verify both jog outputs, 1200/1800 µs target changes at the scheduled times, neutral before the 10.5-second cutoff, emergency stop/disconnect during jogging and timer rollover during a jog. Both the host checks and full target build passed. The first restricted target build's linker was terminated with signal 9; a repeat with project-tool execution access completed successfully.
- Version 0.3 host tests additionally verify both small-motion outputs, the 1450/1550 µs target sequence, neutral before the 7.5-second cutoff, emergency stop/disconnect and timer rollover. The host checks and full target build passed.
- VS Code task JSON, Python syntax and whitespace checks.

The newer native linker prints warnings for unimplemented POSIX file-descriptor/syscall stubs in Newlib. The build succeeds; this sketch does not use those POSIX interfaces. The vendor UF2 conversion script also emits a Python regex-escape warning. Neither warning was suppressed.

## Hardware status

The connected USB device is identified as **Seeed XIAO nRF52840 Sense** (VID 2886 / application PID 8045). At upload, the user confirmed the battery was unplugged and both horns were off.

**Firmware upload confirmed:** after entering bootloader USB PID **0045**, the native Python uploader flashed the compiled DFU package and returned **`Device programmed.`**. A subsequent USB check received **`ROBOT SERVO CENTER 0.1`**, the command menu and **`OFF.`**. The verification sends only `help` and `off`, both disarming commands, and closes the serial connection afterward.

Bootloader mode was identified by USB enumeration; the user did not observe the expected pulsing red LED, so LED appearance alone was not used as the readiness check. An earlier attempt in application mode timed out. Adafruit-nrfutil can return process status zero despite a failed upload; the project upload script therefore requires its explicit positive acknowledgement.

The bundled Servo implementation was inspected: its 20 ms period is 50 Hz and its 8 µs duty resolution rounds a 1500 µs request down to approximately 1496 µs. Host tests check the requested value, not physical pulse timing.

Power-only, neutral and bounded jog commands have been acknowledged, as recorded below. The user confirmed visible movement on both servos. No PWM timing measurement, low-voltage cutoff test or mechanical fit test has been performed by the agent. Electrical measurements below were taken and reported by the user; the agent has no direct voltage or motion telemetry. Host tests do not verify physical GPIO voltages or wiring.

## User-reported electrical checks

All powered checks used the Pololu slide in **OFF**. Both servo horns remain off. The user confirmed no wire is attached to XIAO 3V3, and Pololu VIN connects to the battery-positive bus shared with XIAO BAT+.

| Check | Reported result |
|---|---|
| Battery terminal voltage | 3.963 V |
| Pololu VIN to common GND | Approximately 3.9 V |
| XIAO GND to negative bus, USB and battery unplugged | Approximately 0 ohms |
| XIAO GND to Pololu GND, USB and battery unplugged | Approximately 0 ohms |
| USB only: XIAO 3V3 to its own GND | 3.3 V |
| Battery only: XIAO BAT+ to its own GND | 3.9 V |
| Battery only: XIAO 3V3 to its own GND | 3.27 V |
| USB and battery: repeat XIAO 3V3 to its own GND | 3.3 V |
| Earlier reported resting Pololu VOUT | 0.7 V, then 1.17 V, then 3.9 V; slide position for the last reading was initially unclear |
| Explicit physical slide position check: VOUT | OFF approximately 1.1 V; ON approximately 3.9 V |
| USB and battery: XIAO D2 to XIAO GND | 0 V |
| USB and battery: Pololu ON to the same XIAO GND | 0 V on latest check |

An early XIAO 3V3 reading of 1.1 V was not reproduced in the subsequent supply checks. An early Pololu ON reading of 1.11 V relative to Pololu GND was not reproduced when both control-wire ends were measured using XIAO GND. No cause has been established for these differences; do not infer that an intermittent connection has been ruled out. A reported approximately 2-megohm VIN-to-VOUT resistance does not check for a power-to-ground short.

The agent repeated the USB `help`/`off` check and received the expected version banner and `OFF.` acknowledgement. The reported 3.9 V resting VOUT initially stopped preparation for the timed power test; at that point no `power`, `lower` or `upper` command had been sent. Another `help`/`off` check also received the expected acknowledgement. The subsequent explicit slide-position check shows that the mechanical switch changes the output voltage.

Pololu states that the [disabled output is disconnected and floating](https://forum.pololu.com/t/reverse-voltage-on-mini-mosfet-slide-switch-with-2810/11758). The guide's earlier expectation that OFF must measure near 0 V was too strict and has been corrected. The approximately 1.1 V OFF reading is compatible with a floating output, but its source/current capability has not been determined; no light-load resistor test was performed.

## Supervised software switch test

The user explicitly confirmed the meter was positioned, the slide was OFF and both horns were off. The agent opened USB serial, verified the expected version and disarmed acknowledgement, then sent **one `power` command**. No PWM command was sent. The firmware replied:

```text
POWER ONLY: measure VOUT to GND now; off in 3 seconds.
OFF: test timer expired.
OFF.
```

The final acknowledgement followed an additional explicit `off`; the serial connection was then closed. The command/timeout path is confirmed by USB responses. The user reported that VOUT went down to **0 V during the test** and read approximately **3 V afterward**. This does not match the expected active-high ON behavior; meter timing, probe/pad identification and wiring remain unverified. This initially paused servo tests. The user subsequently confirmed D2 is connected to **ON** and requested an unloaded motor observation instead of further probe measurements.

**Electrical software switching has not passed full commissioning.** Subsequent unloaded motion was confirmed on both servos, as recorded below; shutdown under a known load and supply sag under servo load remain unverified. A serial acknowledgement or successful movement does not establish physical power isolation or electrical switching time.

## Unloaded neutral command and visible-motion firmware

At the user's request, the agent sent `lower` once using version 0.1, with both horns off. The firmware acknowledged `LOWER: 1500 us, off in 15 seconds.`, followed by the timeout and an additional explicit `OFF.`. The serial connection closed afterward. The user said they were not watching, so no physical movement or settling result is established.

The user requested a repeat with larger visible movement. Version **0.2** adds `lower-jog` and `upper-jog`, each commanding **1500, 1200, 1800, 1200, 1800, 1200, 1500 µs**, approximately 1.5 seconds per target. It stops PWM and commands the rail off after 10.5 seconds. Only the selected servo receives pulses, and stop/disconnect handling remains active. This is an unloaded test with both horns removed, not calibrated angle or endpoint motion. The user confirmed the battery was unplugged and USB remained connected for the firmware update.

Version 0.2 was flashed using Arduino CLI and the native uploader, which returned **`Device programmed.`**. A disarming USB check then received **`ROBOT SERVO CENTER 0.2`**, the updated menu and **`OFF.`**. No reset-button intervention was needed for this update.

After the user reconnected the battery and confirmed readiness, the agent sent `lower-jog` once. The firmware acknowledged the jog, its timer expiry and the additional explicit `off`. The user confirmed **the lower servo moved**. The same test then ran once on the upper servo, with the same shutdown acknowledgements; the user confirmed **the upper servo also moved**. The serial connection closed after each test. No sustained-buzzing or settling assessment was separately reported.

## Assembly neutral

The user requested both servos be placed at neutral for installing the horns. The agent sent `lower` and `upper` sequentially at nominal **1500 µs**, holding each for approximately three seconds and explicitly stopping it before proceeding. The firmware acknowledged both neutral commands and each `OFF.`; the serial connection then closed. Both last commanded positions are the assembly zero at nominal 1500 µs. There was no full-range sweep or measurement of the true mechanical travel midpoint. Horns should be fitted with USB and battery disconnected, without rotating the shafts; small spline alignment offsets can be calibrated later.

## Small-motion checks with horns installed

After installing the horns, the user requested smaller movements. Version **0.3** adds `lower-small` and `upper-small`: nominal **1500, 1450, 1500, 1550, 1500 µs**, approximately 1.5 seconds per target, followed by PWM stop and a power-off command at 7.5 seconds. Actual angles remain uncalibrated. Only the selected servo receives PWM; the user supports the arm and checks clearance because the other joint is not actively held.

The user confirmed the battery was unplugged, USB connected and both joints clear for upload. Arduino CLI/native uploader reported **`Device programmed.`**. A subsequent disarming USB check received **`ROBOT SERVO CENTER 0.3`**, its new small-motion commands and **`OFF.`**.

After the user reconnected the battery and confirmed readiness, `lower-small` ran once, followed by its timer-expiry acknowledgement and an explicit `OFF.`. The user confirmed the lower movement was **clear and unobstructed**. `upper-small` then ran once, also followed by its timer-expiry acknowledgement and an explicit `OFF.`; the serial connection closed after each test. The user confirmed the upper movement was also **clear and unobstructed**. Both joints' last commanded target was nominal 1500 µs, and PWM stopped afterward.

The 1200–1800 µs `*-jog` commands remain explicitly labeled **HORNS OFF ONLY** in the menu. Small movements do not establish full joint limits, loaded power margin, physical power isolation or precise angle calibration.

## Rev B direct-battery change

At the user's request, the current design omits the Pololu and its D2 lead, merging the former positive buses into one four-way VBAT+ bus and removing the switch's ground branch. The user confirmed both existing servo connectors are removable three-pin plugs; no extra disconnect component is added. For routine charging and USB-only programming, unplug both complete servo plugs. Battery-only operation is manually switched by the RCY connector; full OFF requires USB removed too.

Version **0.4** defaults to `ROBOT_USE_POWER_SWITCH=0`. D2 is an unused input and receives no GPIO writes. `power` does not energize or arm anything; motion/stop commands retain their PWM behavior, and every stop is explicitly described as PWM-only. Optional `ROBOT_USE_POWER_SWITCH=1` retains compatibility with the archived switched topology. Host tests pass for **both** profiles, including D2 isolation and no-op `power` in direct mode, existing timed motions, disconnect and emergency stops. No Rev B hardware claim follows from host tests.

**Native version 0.4 target build is not verified.** Build attempts ended with externally terminated processes (signal 9 in compiler tools including `as` and `cc1`), and one attempt reported an invalid Arduino instance. A single-job retry also encountered signal 9. The cause is undetermined; no operating-system security settings were changed. There is no successful target-size result for 0.4 and no firmware upload was attempted. The upload command rebuilds first and aborts on build failure, so it will not intentionally upload an old cached package after an unsuccessful build.

The new Rev B one-page SVG/PDF/PNG and both phone diagrams were regenerated and visually inspected. The PDF is a single US-Letter landscape vector sheet, and its PNG preview is rendered from that actual PDF. No overlaps or clipped labels were observed. Rev A drawings remain explicitly archived in the electrical guide.

Re-run software checks with:

```sh
python3 scripts/robot.py test
python3 scripts/robot.py build
```

## Rev B live wiring and compound-motion request

The user confirmed physical rewiring without the Pololu. Existing firmware accepted both small-motion commands and both individual 1200–1800 us jogs, with timeout and explicit OFF acknowledgements. The user confirmed the larger lower-joint swings were clear. The upper jog also completed in software; no separate physical-observation response was received before the user requested compound motion and more range.

Version 0.5 adds a second Servo instance and explicit `dance` command. Both joints interpolate with smoothstep between paired 1100–1900 us targets, returning to nominal 1500 us and holding neutral for 1.5 seconds before stopping PWM at 14.1 seconds. Boot remains disarmed; timeout, serial disconnect, emergency stop, malformed commands and attachment failures stop both channels. Host tests pass in both power profiles, including every millisecond of the dance bounds, keyframes, neutral finish, second-channel attachment failure and rollover. These tests do not establish physical clearance or real PWM timing.

The first version 0.5 sandboxed build was killed; the next elevated attempt reached linking but `ld` was killed with signal 9. The installed older Seeed compiler cannot run on this Mac (`bad CPU type`). Running the native linker's version query succeeded, and a subsequent cached native build completed with exit code zero (CLI reported it could not determine program size). No security settings were changed.

Version 0.5 was uploaded to `/dev/cu.usbmodem101`; the uploader returned `Device programmed.`. A USB handshake verified `ROBOT SERVO CENTER 0.5` and `OFF.` before motion. One `dance` command then returned `DANCE: BOTH joints 1100-1900 us, neutral then PWM off in 14.1 seconds.`, followed by `OFF: test timer expired.` and the explicit additional `OFF.`. The firmware also stated that direct servo power remains connected. Serial closed afterward. Physical dance clearance/return observation is awaiting user feedback; the acknowledgements establish command execution, not measured shaft positions.

## Version 0.6 smoother dance

The user observed jerkiness during version 0.5's dance. Version 0.6 retains the 1100–1900 us range and paired waypoints, replacing cubic smoothstep with quintic minimum-jerk interpolation (zero first and second derivative at segment endpoints). Segments increase from 1.8 to 3.2 seconds, targets update every 20 ms, and total runtime becomes 23.9 seconds including the final 1.5-second neutral hold. This does not smooth acquisition from an unknown physical starting pose. Host tests pass in both power profiles and verify target updates only on scheduled frames, per-frame changes at most 11 us before hardware quantization, bounds, waypoints, neutral finish and both-output stop paths. Physical improvement requires user observation.

The native target build succeeded: 51,576 bytes flash and 7,720 bytes global RAM. The uploader returned `Device programmed.` for version 0.6.

The USB handshake verified version 0.6 and `OFF.`. One smoother `dance` then ran, acknowledging its 23.9-second duration, timer expiry, and an additional explicit `OFF.`; serial closed afterward. Nominal final targets were 1500 us on both joints. Direct power remains connected. Whether the physical motion is smoother awaits user observation.

## Version 0.7: finer PWM and continuous motion

The user reported version 0.6 was still insufficiently smooth. Inspection of the installed ServoTimers.h and Servo.cpp confirmed that pulse commands were divided by 8 using integer division (8 us output increments). Version 0.7 replaces Servo with a project-owned FineServo adapter using the installed core HardwarePWM API: DIV16 on the 16 MHz source, COUNTERTOP 20000, same 50 Hz frame rate and 1 us command increments. Both joints share an owned PWM peripheral; detaching one preserves the other's channel, and the final detach stops/releases the peripheral. Pulse requests are clamped to the attachment bounds. Downloaded dependencies and operating-system settings are unchanged.

The dance now uses continuous phase-offset sine/cosine targets with 8-second period and 4-second quintic amplitude fade-in/out, over 24 seconds plus 1.5 seconds neutral hold. Range remains 1100–1900 us; there are no intermediate stop-at-waypoint transitions. Initial acquisition from an unknown shaft pose remains unsmoothed. Sketch host tests pass for both power profiles, including frame cadence, pulse bounds, per-frame step bounds, neutral finish and stop paths. Separate tests compile the actual FineServo header against a fake core API and verify every integer pulse value from 1000 to 2000, period/prescaler configuration, independent channels, clamping, ownership failure and detach behavior. These are not oscilloscope measurements or physical smoothness verification.

Native build succeeded: 56,036 bytes flash and 7,624 bytes global RAM. Upload returned `Device programmed.`; a USB handshake verified version 0.7 and `OFF.` before motion.

Version 0.7's single dance completed with its timer expiry, explicit OFF acknowledgement and serial close. The user then requested battery telemetry, avoiding over-discharge, faster motion and continuing to dance until instructed to stop.

## Version 0.8: voltage guard and continuous faster dancing

The native build passed at 58,776 bytes flash and 7,664 bytes global RAM; upload returned `Device programmed.`. Host tests pass for both power profiles and the actual PWM adapter. New tests verify ADC conversion, refusal to arm below the start threshold, heartbeat refresh/expiry, two-sample low-voltage stopping, invalid ADC stop and disconnect/emergency-stop paths.

The implementation uses installed board mappings VBAT_ENABLE (Arduino 14 / P0.14, held LOW) and PIN_VBAT (Arduino 32 / P0.31), matching Seeed's [classic Sense documentation](https://wiki.seeedstudio.com/XIAO_BLE/) and [schematic](https://files.seeedstudio.com/wiki/XIAO-BLE/Seeed_Studio_XIAO_nRF52840_PDF.pdf). Conversion assumes 1 MOhm/510 kOhm divider, internal 3.0 V full-scale, 12-bit ADC and 40 us acquisition. It averages eight samples after discarding one. No meter calibration is claimed. Before motion the estimate must be 3.7–4.4 V. Sampling every 100 ms while moving stops both PWM channels after two readings below 3.6 V, immediately below 3.4 V, or above 4.4 V. This is not a physical battery cutoff and cannot prevent continued idle discharge after stopping.

At the user's explicit request, `scripts/dance.py` was started for continuous supervised operation, rather than a finite one-shot. The host verified firmware 0.8 and OFF, read **4074 mV**, and started `dance-loop`. Firmware acknowledged **4-second cycles, 1100–1900 us** (twice the timed dance's frequency), with a 4-second amplitude fade-in and no periodic stop/recenter. Initial motion readings were **4011–4074 mV**, uncalibrated with USB connected. The host sends `keep` every 2 seconds; firmware stops if this is missed for 5 seconds or serial disconnects. The host writes a PID and voltage log to ignored build/dance.pid and build/dance.log, exits on guard stop and never automatically restarts. Current live operation must be checked in that log; this entry is a start record, not a claim that dancing remains active indefinitely.

## Version 0.9: faster cycles and fixed timing

At the user's request for faster and smoother movement, the continuous period changes from 4 seconds to 2.5 seconds (1.6 times the frequency). Range, 4-second fade-in, 1 us PWM, 50 Hz pulse rate, battery thresholds, heartbeat and explicit stop behavior are retained. Motion targets now use a fixed 20 ms time grid instead of moving the next update deadline each time an iteration runs late. This prevents accumulated target-update timing drift; it is not a claim of measured mechanical improvement. The 8-second timed dance is retained. Host tests pass for both power profiles and the actual PWM adapter; added coverage runs 60 simulated seconds of continuous motion, checks pulse bounds/frame-step bounds and verifies recovery to the original schedule after a late update. The existing physical dance remains running during the build; upload requires a brief explicit stop and restart.

Native build succeeded at 58,800 bytes flash and 7,664 bytes global RAM. The previous host was signaled to stop; its PID file was removed after the explicit PWM stop/serial close. The completed build was uploaded without rebuilding; uploader returned `Device programmed.`. The continuous dance host was restarted for version 0.9; the live start acknowledgement and battery readings are recorded in build/dance.log. Physical smoothness is awaiting user observation.

## Version 0.10: faster loop, finer setpoint cadence, live tempo

The user again requested faster and smoother motion. The default loop period changes from 2500 to 1600 ms and the setpoint time grid from 20 to 5 ms; physical pulse rate remains 50 Hz at 1 us resolution. ADC thresholds, heartbeat, full 1100–1900 us range and continuous operation remain unchanged. A new `tempo N` command (1000–10000 ms) preserves instantaneous phase and angular velocity, then blends to the requested angular velocity over 2 seconds using quintic interpolation and its analytic integral. It does not start motion from idle. The host's `--period-ms` argument sets startup period; editing ignored build/dance-period-ms sends subsequent requests over the existing serial connection, without reopening it or restarting the robot. Invalid host file contents are ignored; malformed/out-of-range firmware tempo commands stop PWM.

Host tests passed for both power profiles and the actual FineServo adapter, including phase/velocity continuity on a tempo change, final requested angular velocity, invalid values and no idle arming. The 60-second simulated continuous test retains pulse and per-update bounds. Python syntax and whitespace checks pass. Native build passed at 60,096 bytes flash and 7,680 bytes global RAM. Physical smoothness remains unmeasured; an optional user question asks whether remaining roughness appears as stepping, reversal kick or structural shake.

Uploader returned `Device programmed.`. The restarted host verified version 0.10, read 4055 mV, received `DANCE LOOP: 1.6-second cycles, 1100-1900 us, battery guard and heartbeat enabled.`, then `TEMPO_MS: 1600`. Initial moving estimates were approximately 4029–4051 mV. Continuous operation remains active; current state is in build/dance.log. No new user judgment of physical smoothness is recorded yet.

## 1 November 2026: IMU commissioning, no motor outputs

The user confirmed battery and both complete three-pin servo plugs disconnected, USB connected. The sensor-only sketch replaced servo bench 0.10 on the board; normal `upload` still selects the bench program, while `upload-imu` selects this diagnostic. The earlier dance start records above are historical and do not describe the now-uploaded firmware.

The initial 0.1 upload acknowledged programming but returned no USB banner. Replacing unbounded Wire1 event waits with a project-owned, deadline-based TWIM1 transport restored diagnostics in 0.2, which reported no IMU response. Version 0.3 matched Seeed's **high-drive power GPIO configuration** and power-cycled the IMU at startup; hardware identity 0x6A at address 0x6A and configuration readback then passed with zero I2C errors. See [Seeed's driver](https://github.com/Seeed-Studio/Seeed_Arduino_LSM6DS3/blob/master/LSM6DS3.cpp) for the high-drive setting. A host handshake fix requires a complete status response after OFF acknowledgement, avoiding truncated startup-banner tails.

The first stream exposed unsigned time underflow when a USB command started streaming after the loop-entry timestamp. Version **0.4** samples time again after command handling. A host test with nonzero serial-print time covers that regression. The native build uses **55,520 bytes program storage and 7,576 bytes static RAM**; upload acknowledged `Device programmed.` and a subsequent USB status verified 0.4, `IMU_READY: 1`, correct identity/configuration and zero I2C errors.

An initial unconfirmed-pose recording yielded 500 clean samples. The user then confirmed the board fixed to the base and three specific orientations: base flat/upright, base vertical with lower output-horn side up, and base horizontal/inverted with the arm supported. Each ten-second known-pose recording yielded 501 samples, with no I2C errors, saturation, duplicated samples or gaps above 40 ms. Upright acceleration norm averaged 1.011 g and the stationary sensor-frame gyro mean was approximately [0.00286, -0.02271, -0.00690] rad/s.

Upright and horn-side-up observations fit a proper sensor-to-CAD rotation with 0.93° residual per pose. The independent inverted recording was excluded from fitting and bias estimation; its mean gravity direction checked at 2.41° from expected, below the 5° static-screening threshold. The inverted capture includes modest hand-held motion, so this is not precision fixture calibration. Raw CSVs, summaries, source hashes and the provisional rotation/bias are [preserved with the measurements](imu_bench/measurements/2026-11-01/commissioning.json).

No sensor calibration has been applied to firmware, no attitude estimator or learned policy is enabled, and no physical motor commands were sent. Both signal pins remain LOW. BAT readings in these USB-only records are the charger/BAT node with the cell unplugged, not battery state of charge. Dynamic gyro validation, actuator mapping/dynamics, high-resolution timing and policy shadow tests remain pending.


## 1 November 2026: filtered policy shadow, motor outputs disabled

Policy shadow **0.1** replaced IMU bench 0.4 after the user-confirmed USB-only setup. The native build passed at **82,320 bytes flash / 7,736 bytes static RAM**, and the uploader returned `Device programmed.`. The USB recorder subsequently verified `ROBOT POLICY SHADOW 0.1`, IMU/filter readiness and disabled motor outputs. The sketch contains no servo/PWM driver and holds D0/D1 LOW; D2 remains unused.

The provisional mounting rotation and recorded gyro bias are now applied. A portable gravity-direction filter combines gyro propagation with gated accelerometer correction. Policy timing uses a project-owned 1 MHz TIMER4 counter; core micros/DWT behavior is unchanged. Build optimization is explicitly `-O2` to preserve finite-value guards. The actor and original training weights are unchanged.

The first ten-second shadow capture, whose physical pose was not independently confirmed, contains **500 frames**, zero I2C errors and no saturation. Inference was **1,199 µs median / 1,208 µs maximum**. MCU actions differed from the host C actor by at most **2.32e-7**; virtual targets/history and unit-DOWN checks passed. Maximum policy deadline lateness was **1,376 µs**, with no frames over 10 ms late. Maximum sample age was **8,312 µs**. Sample timestamp differences average 20,002 µs; the varying individual intervals reflect 208 Hz sensor timestamps, not policy invocation timestamps. The 19 filter-reject counts are expected startup warmup and did not increase during capture.

MuJoCo now optionally invokes an observer after every physics step. The exploratory evaluator compiles the exact firmware filter, feeds simulated specific force/gyro through mounting/bias/noise/clipping and evaluates the unchanged actor. Initial development results were **22/30** (eight unready filters), refined results **28/30** on that same set (one unready), and a fresh seed set **26/30** (zero unready). The refinement requires stationary initialization and distinguishes accelerometer clipping from gyro clipping. All failures are preserved; earlier 100/100 ideal-orientation evaluations are not filtered sensor validation. A paired diagnostic on the fresh 30 seeds, replacing only the actor’s DOWN input with exact orientation while retaining simulated sensor gyro, recovered in **30/30**. This isolates orientation-estimation sensitivity in the tested model. No physical recovery or actuator response is tested by virtual targets.

Source/image hashes, raw capture, MCU/host parity, timing and per-trial simulation results are [recorded together](policy_shadow/results/2026-11-01/commissioning.json). Filter analytic tests and actual-sketch fake USB/I2C/clock tests pass, including ten seconds of full rotations, acceleration rejection, antipodal correction, finite-value/timestamp checks, startup, disconnect, timeout, action history, slow USB and clock rollover. A physical dynamic orientation check and actuator mapping/dynamics remain pending. BAT values in the USB-only capture are not actual cell voltage.


## 2 November 2026: guided manual rotation, still no motor outputs

The user reconfirmed battery and both complete servo plugs disconnected, USB connected, and readiness to rotate the whole robot while supporting the arm. The XIAO reappeared at `/dev/cu.usbmodem101` (same VID/PID and serial identity). A 20-second capture logged **1,000 frames**; the user reported rotating it approximately three times. The estimate spanned **1.68–173.62°** tilt, without I2C errors, saturation, additional filter rejects or policy frames more than 10 ms late. Actor inference was **1,224 µs median / 1,238 µs maximum**, and maximum MCU/host action error **5.74e-7**. Virtual target/history and unit-DOWN checks passed. The 19 filter rejects remained unchanged throughout, matching initial warmup.

An explicit `off`/status exchange afterward acknowledged shadow stopped, IMU/filter ready, zero I2C errors and disabled motor outputs. A subsequent five-second capture added **250 frames**, with stable estimated tilt **1.49–1.50°**, no I2C errors/saturation, 1,202 µs median inference and MCU/host action error below 2.42e-7. The flat pose was requested but not independently measured. These observations establish qualitative continuity and settling, not dynamic angular accuracy; there is no external orientation reference. No PWM or learned physical control was enabled.

[Raw captures and summaries](policy_shadow/results/2026-11-02/manual_check.json) preserve file hashes, assumptions and remaining actuator/dynamic sensor work. The previous session’s last USB status attempt was blocked by an automatic-review usage-limit failure; today's retry and recording succeeded. No bypass or wiring change was used.


## 2 November 2026: visual servo-calibration tool, initially disarmed

The user chose easily recognized 45°/90° poses instead of a precision gauge. A separate calibration sketch starts with both signals LOW, selects one joint at nominal 1500 µs only after an explicit command, and supports target increments no larger than 50 µs with at most 1 µs applied change per 10 ms after initial acquisition. One-second host heartbeats, five-second timeout, 120-second absolute session duration and existing ADC battery guards bound supervised motion. Initial acquisition cannot be position-aware because no shaft feedback is exposed. No endpoint is swept automatically.

Native build passed at **48,316 bytes flash / 7,680 bytes static RAM**, using `-O2`. Actual-sketch fake-hardware tests passed for single-joint operation, incremental slew without delayed-loop jumps, command/parser/window bounds, failed PWM attachment, battery guards, emergency/disconnect/timeouts and rollover. The uploader returned `Device programmed.`. The new recorder verified the full `ROBOT SERVO CALIBRATION 0.1` banner and `ACTIVE_JOINT: -1`; this first connection sent no movement commands. A kinematic CAD reference image shows straight and signed ±45° poses.

[Deployment hashes and disarmed handshake](servo_calibration/results/2026-11-02/deployment.json) are recorded. Physical pulse-to-angle observations, sign confirmation and clearance measurements are still pending. The interactive recorder saves manually observed angles with fresh settled PWM telemetry, explicitly marked approximate and provisional; it does not update policy/simulator calibration automatically. The current board runs this calibration firmware, replacing policy shadow 0.1; `upload-shadow` remains available.


## 2 November 2026: six visually observed servo angle references

After the user confirmed battery and servo plugs reconnected and both links supported, the new host selected the lower joint at 1500 µs. At the user's request, it first cycled lower and upper individually through 1400–1600 µs, returning each to 1500 µs. No angle observations were inferred from those commands alone.

The user then explicitly confirmed both joints straight at **1500 µs**, approximately **45° at 1900 µs**, and approximately **45° on the opposite side at 1100 µs**. Lower 1900 leaned toward the battery; upper 1900 toward the XIAO edge. With the CAD +X lower / +Y upper axes, both pulse slopes are **negative**: +45° at 1100, 0° at 1500, −45° at 1900. The resulting provisional slope is −8.8889 µs/degree (−509.30 µs/radian). These are unquantified visual estimates, one observation per pose; no claim of precision, full travel, backlash or loaded dynamics follows.

The session preserved **10,949 telemetry rows**, six manually confirmed observations and raw serial responses. Each observation matches its recorded applied-pulse row. USB-connected battery estimates spanned **4.124–4.156 V**; they are not current/brownout or net-charging measurements. A 120-second timeout stopped PWM during one lower return at 1650 µs, and the subsequent set command was refused while inactive. Explicit reselect resumed at nominal 1500 µs; no guard was bypassed. Final telemetry records each joint last commanded to 1500 µs, followed by acknowledged OFF and recorder close. The user was asked to disconnect battery and USB; no hardware power-disconnect confirmation is claimed.

The [reviewed mapping and raw evidence](servo_calibration/results/2026-11-02/visual_mapping.json) record signs, knots, hashes, limitations and stop events. The raw recorder metadata is kept unchanged; reviewed CAD signs live in the separate mapping and CAD joint map. An offline interpolation utility refuses outside ±45°, non-finite angles, unreviewed signs and inconsistent knots. Its three tests pass, checking provenance, both joint reference points, intermediate values and refused ±80°/±90° extrapolation. It sends no motor commands. No policy weights, XML joint signs/limits or deployed firmware changed in this measurement stage.


## 2 November 2026: trained-range controller deployment and no-PWM check

The user explicitly requested the trained ±80° range rather than a ±45° deployment cap. The separate supervised controller 0.1 keeps the exported actor, 50 Hz policy grid, 10-input observation contract and 0.06-radian incremental actions unchanged. It uses the confirmed negative PWM signs and a declared linear extrapolation from the visual ±45° references to **789–2211 µs**. Original measurement data/tool bounds are unchanged; no new end-stop or clearance validation is inferred.

The user also flagged broad adjacent-body contact exclusions as a mistake to correct at the next training pass. The exclusions originally avoided artificial forces at fitted pivot/housing surfaces but suppress genuine clashes elsewhere. This correction is explicitly recorded in the training plan and backlog; selective mating-surface treatment, full-range/dynamic collision audits and retraining are required then. Current weights/XML remain unchanged for the user's authorized deployment.

The actual-sketch tests and existing regression suite passed, including the real actor, ±80° PWM endpoints, one-second neutral hold, target/history integration, shadow isolation, attach failure, battery/sensor/non-finite/USB/heartbeat/deadline/session/input stops, bounded nonblocking telemetry and timer rollover. The host supervisor analyzes telemetry from the actual fake-hardware sketch successfully. Native build uses **84,600 bytes flash / 7,880 bytes static RAM**, `-O2`.

With the user's confirmed USB-only setup (battery and complete servo plugs disconnected; base flat/still), upload acknowledged `Device programmed.`. The ten-second no-PWM check captured **500 frames**, **zero I2C errors**, **zero dropped telemetry** and both PWM fields zero. Inference was **1,217 µs median / 1,225 µs maximum**, maximum lateness **1,382 µs**, sample age **5,169 µs**. MCU/host action difference from 1e-6-quantized observations was at most **1.29e-6**; history, integration and unit-DOWN checks passed. An explicit OFF was acknowledged. [Source/image hashes and raw telemetry](policy_control/results/2026-11-02/deployment.json) are preserved. This is not a physical recovery test.


The first live trial then ran 15 seconds from the user's confirmed upright setup with both servos and battery connected. All **750 frames** completed, zero I2C errors/dropped rows; inference **1,218 µs median / 1,225 µs maximum**, deadline lateness **1,379 µs**, sample age **5,626 µs**. Host/MCU action error from quantized observations was **1.37e-6** and target/history/PWM checks passed. BAT estimates with USB were **4.126–4.147 V**. The full trained ±80° range was available, while actual targets reached at most **18.48°**. OFF was acknowledged. The user confirmed both joints moved freely and the robot remained standing without reported clashes/buzzing. This is an upright control-loop test; sideways recovery and full-range physical clearance are not established by it.


## 2 November 2026: first user-confirmed unassisted self-righting

For the next 15-second run, the user confirmed the robot resting sideways, base vertical, lower horn side up, with cable slack, and watched. The run completed **750 frames**, zero I2C errors or dropped telemetry, **1,230 µs median / 1,272 µs maximum inference**, **1,378 µs** maximum lateness and **5,222 µs** maximum sample age. Numerical checks passed. Full ±80° target limits were reached, with commanded pulse extrema **789–2211 µs**. USB-connected BAT estimates were **4.123–4.150 V**. OFF was acknowledged.

The estimated initial/final base tilts were **98.59° / 1.52°**. Asked separately, the user confirmed **it got upright without assistance** and **they disturbed it again during the run**. Exact disturbance times/count are not established. This supports a first real self-righting demonstration, not an untouched benchmark trajectory, repeatability statistic or full collision-clearance validation. [Telemetry and operator observations](policy_control/results/2026-11-02/sideways_observation.json) preserve that distinction.

The host process exited after stopping; the user was asked to disconnect battery and USB for full power-off. No physical disconnect confirmation is claimed. The deployed program boots disarmed and still requires USB heartbeat; standalone arming/stop operation remains a subsequent step. Collision correction/retraining is deferred as requested, with current trained weights and XML unchanged.


## 7 November 2026 — D8 lower / D7 upper signal reroute

The user reports signal wiring on printed 8 (lower) and 7 (upper). All maintained sketch sources now use D8/D7, including boot, inactive, charge and fault paths. Controller 0.4 reports the pin mapping in its status banner. The actor weights, IMU estimator, angle calibration and simulator are unchanged. Historical records above still describe their original pins and physical deployments.

The native controller build passes at **85,940 bytes flash / 7,880 bytes static RAM**. The complete firmware host regression and **nine** Mac-helper tests pass. Checks include joint ordering on 8/7, high-numbered PWM pins, disabled outputs on faults/charge, and rejection of old 0.2/0.3 controller banners before arm/charge. Charging-version verification permits an unready IMU. The Rev C PDF/SVG/PNG and phone map match the new pins.

This is an offline build/source change: **no upload, serial commands or physical joint test**. See [controller 0.4 instructions](policy_control/README.md#signal-pin-reroute-04--7-november-2026) and [build/provenance record](policy_control/results/2026-11-07/pin_routing_0_4.json).

Native target builds also pass for all maintained auxiliary sketches: servo bench, servo calibration, IMU bench, policy shadow and arithmetic probe. Pin-update record includes flash/RAM sizes for all six targets.


## 7 November 2026 — controller 0.4 uploaded and running

After the user explicitly requested connected-harness upload, the existing controller acknowledged PWM OFF and DFU acknowledged **Device programmed.**. The disarmed 0.4 banner confirms lower D8 / upper D7. The no-PWM check passed **150/150 frames**, zero I2C errors/dropped rows, **1,200/1,206 µs median/max inference**, and **1.21e-6** action parity error. Both PWM fields stayed zero; OFF was acknowledged.

Standalone arming was confirmed; a subsequent non-stopping state read reached frame **1,231**, mode 4, ready sensors, zero I2C errors and USB-connected BAT estimate **4.137 V**. The user confirms both joints respond normally, without binding or sustained buzzing. Control was left running at the user's request. No new unassisted recovery score, isolated angle verification or charging-cycle result is inferred. [Deployment record and captures](policy_control/results/2026-11-07/deployment_0_4.json).
