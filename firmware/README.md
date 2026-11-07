# Rev B terminal control - direct battery power

**7 November 2026 source update:** all maintained sketches now use **D8 / 8 for lower PWM** and **D7 / 7 for upper PWM**, including boot/stop/no-motion paths. The recovery controller **0.7** is uploaded with the C3 PPO actor, automatic battery-only startup, USB-at-boot charge mode and the reboot-only 60-second base-IMU inactivity lock. Earlier 0.4 passed 150 no-PWM frames and standalone arming on 7 November 2026. References below to earlier builds/uploads are historical. The bench program keeps its existing command protocol/banner; its help now names D8/D7.

> **Current recovery/Rev C workflow:** use [policy controller 0.7](policy_control/README.md), [operating instructions](../docs/OPERATING_INSTRUCTIONS.md) and the [single-Pololu schematic](../electrical/README.md). Version 0.7 is uploaded and includes automatic battery-only startup, USB-at-boot charge mode, a reboot-only inactivity lock, `./robot charge` and D8/D7 routing; charging acceptance remains pending. The bench-sketch Rev A/B wiring and charging procedures below are historical; do not use them to wire the Rev C master switch.

**Currently uploaded: [learned controller 0.7](policy_control/README.md)**, with explicit Mac arming and confirmed standalone battery operation. Version 0.7 was uploaded on 7 November 2026 with the C3-matched PPO actor, automatic battery-only startup, USB-at-boot charge mode, D8/D7 routing and the 60-second base-IMU inactivity stop. Charging remains available after timeout; reboot is required to clear the inactivity lock. It starts recovery on battery-only boot, stays PWM-off on USB boot, and retains the trained ±80° policy and measured negative PWM signs. Use `build-control` / `upload-control` and `scripts/control.py`. The first 500-frame no-PWM hardware check passed. The [visual calibration](servo_calibration/README.md) and [policy shadow](policy_shadow/README.md) remain available through their explicit upload targets. Ordinary `upload` still selects the servo bench 0.10 described below.

**Historical bench-sketch source: version 0.10, direct-powered servos with no Pololu.** D8/marked 8 controls the lower servo, D7/marked 7 controls the upper, and D2 is unused. Both PWM outputs stop on boot, timeout, USB serial disconnect, `off` or `!`. **None of these actions disconnects servo power.** Full OFF requires battery and USB unplugged.

The user confirmed Rev B wiring is live. Version 0.3 has also executed individual joint motions on this harness. Version 0.10 was successfully built and uploaded. It adds battery telemetry and guarded continuous faster dancing to the finer-PWM driver introduced in 0.7; commissioning details and physical observations are recorded separately in the [validation log](VALIDATION.md). Earlier 0.4 target builds were blocked by compiler subprocesses terminated with signal 9. Source defaults to `ROBOT_USE_POWER_SWITCH=0`; setting it to 1 is only for the archived Pololu Rev A harness.

## Build and upload from Terminal or VS Code

For USB-only programming, **unplug the battery and both complete three-pin servo plugs**, then connect USB. Removing only the battery does not isolate the servo-positive bus from the XIAO charger.

```sh
cd "/Users/super23/Documents/BLDC Motor Build/2dof_standing"
python3 scripts/robot.py build
python3 scripts/robot.py ports
python3 scripts/robot.py upload
python3 scripts/robot.py check
```

On a fresh checkout, first run `python3 scripts/robot.py setup`. This macOS setup stores tools under ignored `.tools/` and firmware under ignored `build/`. It pins Arduino CLI 1.5.1 and Seeed's regular/non-mbed nRF52 Boards 1.1.13 with bundled Servo/TinyUSB libraries. Apple Silicon uses native Arm GNU 13.2.Rel1. Python 3.12+, macOS Command Line Tools and network access are needed for setup. No Arduino IDE or VS Code extension is required; the same commands are available under **Terminal -> Run Task -> Robot: ...**.

The upload script accepts only a recognized XIAO nRF52840 Sense and requires the uploader's `Device programmed.` acknowledgement. The `check` command sends only `help` and `off`, checks the 0.10 banner and `OFF.` response, then closes serial. If upload cannot reach the bootloader, double-press reset, list ports and retry. Do not use boot LED appearance alone as proof of bootloader mode.

The separate [policy arithmetic probe](policy_probe/README.md) builds the simulation-trained actor with `python3 scripts/robot.py build-probe`. It generates no servo pulses and has not been uploaded. The normal upload command above still installs the bench firmware.

For the first hardware-deployment stage, the [IMU commissioning program](imu_bench/README.md) uses `build-imu` / `upload-imu` and provides sensor-only acceleration, gyro and battery logging through `scripts/imu.py`. It contains no servo PWM or learned-policy control. Confirm the USB-only, servo-plugs-disconnected setup before uploading it.

## Run movements yourself

With USB and battery disconnected, reconnect the complete servo plugs. Support the arm, check clearance and reconnect the battery, then USB for a supervised terminal test. This is a brief motor test, not unattended charging. Start from the established upright assembly pose.

```sh
python3 scripts/robot.py monitor
```

Serial uses **115200 baud**. Type **one command**, press Enter, and wait for the stop response before another command. Do not paste a whole list of commands at once; each new command replaces the previous test. Exit with **Ctrl+]**. Keep the arm supported after the test too; an unselected servo gets no PWM, and stopped pulses do not guarantee released holding torque.

| Command | Action |
|---|---|
| `battery` | BAT-node estimate in millivolts; no motion started |
| `dance-loop` | Continuous 1.6-second default cycles, 1100–1900 us; requires `keep` every 2 s; 5 s heartbeat timeout |
| `tempo N` | Change active loop period to 1000–10000 ms, blending angular speed over 2 seconds without resetting phase; does not start a stopped robot |
| `keep` | Refresh continuous dance heartbeat; no motion started |
| `dance` | Both joints simultaneously; continuous phase-offset 1100–1900 us waves, neutral hold, PWM stops after 25.5 s; supervised clearance required |
| `lower-small` | D8: 1500, 1450, 1500, 1550, 1500 us; approximately 1.5 s each; stop at 7.5 s |
| `upper-small` | Same small supported-assembly check on D7 |
| `lower` | D8 nominal neutral 1500 us for up to 15 s |
| `upper` | D7 nominal neutral 1500 us for up to 15 s |
| `lower-jog` | **HORNS OFF ONLY:** D8 at 1500, 1200, 1800, 1200, 1800, 1200, 1500 us; stop at 10.5 s |
| `upper-jog` | Same unloaded/horns-off test on D7 |
| `off` | Detach PWM and drive both signal pins LOW; **power stays connected** |
| `!` | Immediate PWM stop without Enter; send a newline before another command |
| `help` | Stop PWM and print menu |
| `power` | No effect in Rev B; the electronic power switch was removed |

The small checks passed on both assembled joints with version 0.3 before rewiring. Actual shaft angles, endpoints, loaded supply margins and Rev B power behavior are not yet characterized. Earlier versions used an 8 us PWM grid; version 0.7 configures 1 us increments. These are nominal commands, not encoder measurements. Do not use wide jogs with installed horns/links until limits are established.

The dance uses continuous sine/cosine targets with an 8-second period, a 4-second quintic fade-in/out, 24 seconds of motion and a final 1.5-second neutral hold. Targets update on a fixed 5 ms grid; late loop iterations do not shift subsequent target deadlines. It no longer stops at intermediate waypoints. The project-owned `FineServo.h` uses the board core's hardware PWM at 1 MHz with a 20,000-tick frame: 1 us pulse increments at the same 50 Hz, replacing the bundled Servo library's 8 us increments. No downloaded core files are patched. Servo deadband, gearing, friction, supply behavior and mechanical flexibility can still affect physical smoothness. Initial center acquisition is not position-aware because these servos provide no feedback.

## Continuous faster dance and battery guard

Use the project Python environment (it contains pyserial):

```sh
.tools/arduino/python/bin/python scripts/dance.py
```

This supervised host verifies firmware 0.10, reads battery voltage, starts `dance-loop`, sends a heartbeat every 2 seconds, and logs voltage to `build/dance.log`. Press Ctrl+C to stop. The process ID is stored in `build/dance.pid`; sending that process SIGTERM also requests an explicit PWM stop. Do not open a second serial monitor while it runs. Firmware stops on USB serial disconnect or a missed 5-second heartbeat. The continuous loop defaults to a 1.6-second cycle (1.5625 times version 0.9's speed), the same range and a gentle initial fade-in. It does not periodically stop/recenter. Set the initial period with `--period-ms 1600`. While the host runs, edit `build/dance-period-ms` to an integer from 1000 to 10000 to send a live tempo request. The host validates the range and firmware preserves phase while blending angular speed over 2 seconds. Smaller numbers mean faster cycles. Invalid firmware tempo commands stop PWM; invalid file contents are ignored. Setpoint calculation at 200 Hz does not change the 50 Hz servo pulse rate or establish measured shaft smoothness.

All motion commands now require a battery estimate between 3.7 and 4.4 V before arming. During motion the ADC samples every 100 ms: two consecutive readings below 3.6 V, one below 3.4 V, or one above 4.4 V stop PWM. The host exits after a guard stop and does not restart automatically. `battery` reads the BAT node using the classic Sense's onboard 1 MOhm/510 kOhm divider, 12-bit ADC, internal 3.0 V full-scale and 40 us acquisition. Results are uncalibrated estimates; USB/charging affects the node voltage, and absent-cell detection, state of charge and current sensing are not provided. This can miss brief brownout transients.

**This is a motion guard, not a battery disconnect.** Servo idle drain continues after PWM stop; unplug battery and USB if voltage is low or for storage. USB's approximately 100 mA charging path may supply less current than dancing consumes, so USB connected does not prove net charging. No claim of unattended over-discharge protection is made.

## Horn installation / neutral

For initial centering, remove horns and driven links, command one servo to nominal 1500 us, stop PWM, and disconnect battery and USB before fitting the OEM horn at the nearest upright spline tooth. Avoid rotating the shaft as you seat it and use the supplied center screw. Repeat on the other servo. Small spline offsets can be calibrated later. With horns already installed, use only the supported small-motion checks after checking clearance.

## Charging and low battery

For routine USB-C charging, **unplug both complete servo plugs**, keep the battery connected to XIAO BAT+/GND and connect USB. The board's charger is not a motor supply. USB can feed the shared BAT+ bus even without a battery, so battery removal alone is not full OFF when USB remains attached. No separate charger or extra disconnect component is added.

The sketch selects approximately **100 mA** via `PIN_CHARGING_CURRENT` LOW and keeps `VBAT_ENABLE` LOW. See [HARDWARE.md](../HARDWARE.md) for pin mappings and charging limits. Rev B has no automatic physical low-voltage cutoff. A future voltage alarm can stop PWM, but servo idle current remains until the pack is unplugged. The voltage motion guard is implemented in version 0.8; it is not a physical cutoff. Disconnect battery and USB for storage.

## Validation and drawing tools

Run `python3 scripts/robot.py test` for host tests of both direct-power Rev B and optional switched Rev A profiles. The [validation log](VALIDATION.md) distinguishes builds, USB acknowledgements and the user's physical observations. No robot commands or uploads were performed during preparation of the Rev B change.

The diagram generators use `reportlab`, `pymupdf` and Pillow in the existing ignored project Python environment. The original Pololu tests remain historical records in the log, not Rev B wiring instructions.
