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
