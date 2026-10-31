# Rev B terminal control - direct battery power

**Current source: version 0.5, direct-powered servos with no Pololu.** D0/marked 0 controls the lower servo, D1/marked 1 controls the upper, and D2 is unused. Both PWM outputs stop on boot, timeout, USB serial disconnect, `off` or `!`. **None of these actions disconnects servo power.** Full OFF requires battery and USB unplugged.

The user confirmed Rev B wiring is live. Version 0.3 has also executed individual joint motions on this harness. Version 0.5 was successfully built, uploaded and verified over USB. Its simultaneous dance ran once with timeout and explicit OFF acknowledgements; physical observations are recorded separately in the [validation log](VALIDATION.md). Earlier 0.4 target builds were blocked by compiler subprocesses terminated with signal 9. Source defaults to `ROBOT_USE_POWER_SWITCH=0`; setting it to 1 is only for the archived Pololu Rev A harness.

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

The upload script accepts only a recognized XIAO nRF52840 Sense and requires the uploader's `Device programmed.` acknowledgement. The `check` command sends only `help` and `off`, checks the 0.5 banner and `OFF.` response, then closes serial. If upload cannot reach the bootloader, double-press reset, list ports and retry. Do not use boot LED appearance alone as proof of bootloader mode.

## Run movements yourself

With USB and battery disconnected, reconnect the complete servo plugs. Support the arm, check clearance and reconnect the battery, then USB for a supervised terminal test. This is a brief motor test, not unattended charging. Start from the established upright assembly pose.

```sh
python3 scripts/robot.py monitor
```

Serial uses **115200 baud**. Type **one command**, press Enter, and wait for the stop response before another command. Do not paste a whole list of commands at once; each new command replaces the previous test. Exit with **Ctrl+]**. Keep the arm supported after the test too; an unselected servo gets no PWM, and stopped pulses do not guarantee released holding torque.

| Command | Action |
|---|---|
| `dance` | Both joints simultaneously; smooth opposing/same-direction 1100–1900 us sweeps, neutral hold, PWM stops after 14.1 s; supervised clearance required |
| `lower-small` | D0: 1500, 1450, 1500, 1550, 1500 us; approximately 1.5 s each; stop at 7.5 s |
| `upper-small` | Same small supported-assembly check on D1 |
| `lower` | D0 nominal neutral 1500 us for up to 15 s |
| `upper` | D1 nominal neutral 1500 us for up to 15 s |
| `lower-jog` | **HORNS OFF ONLY:** D0 at 1500, 1200, 1800, 1200, 1800, 1200, 1500 us; stop at 10.5 s |
| `upper-jog` | Same unloaded/horns-off test on D1 |
| `off` | Detach PWM and drive both signal pins LOW; **power stays connected** |
| `!` | Immediate PWM stop without Enter; send a newline before another command |
| `help` | Stop PWM and print menu |
| `power` | No effect in Rev B; the electronic power switch was removed |

The small checks passed on both assembled joints with version 0.3 before rewiring. Actual shaft angles, endpoints, loaded supply margins and Rev B power behavior are not yet characterized. The nRF52 Servo library quantizes pulses in 8 us steps (1500 us requested is approximately 1496 us); these are nominal commands, not encoder measurements. Do not use wide jogs with installed horns/links until limits are established.

## Horn installation / neutral

For initial centering, remove horns and driven links, command one servo to nominal 1500 us, stop PWM, and disconnect battery and USB before fitting the OEM horn at the nearest upright spline tooth. Avoid rotating the shaft as you seat it and use the supplied center screw. Repeat on the other servo. Small spline offsets can be calibrated later. With horns already installed, use only the supported small-motion checks after checking clearance.

## Charging and low battery

For routine USB-C charging, **unplug both complete servo plugs**, keep the battery connected to XIAO BAT+/GND and connect USB. The board's charger is not a motor supply. USB can feed the shared BAT+ bus even without a battery, so battery removal alone is not full OFF when USB remains attached. No separate charger or extra disconnect component is added.

The sketch selects approximately **100 mA** via `PIN_CHARGING_CURRENT` LOW and keeps `VBAT_ENABLE` LOW. See [HARDWARE.md](../HARDWARE.md) for pin mappings and charging limits. Rev B has no automatic physical low-voltage cutoff. A future voltage alarm can stop PWM, but servo idle current remains until the pack is unplugged. The alarm is not yet implemented. Disconnect battery and USB for storage.

## Validation and drawing tools

Run `python3 scripts/robot.py test` for host tests of both direct-power Rev B and optional switched Rev A profiles. The [validation log](VALIDATION.md) distinguishes builds, USB acknowledgements and the user's physical observations. No robot commands or uploads were performed during preparation of the Rev B change.

The diagram generators use `reportlab`, `pymupdf` and Pillow in the existing ignored project Python environment. The original Pololu tests remain historical records in the log, not Rev B wiring instructions.
