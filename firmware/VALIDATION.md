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
