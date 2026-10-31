# Bench firmware validation — 30 October 2026

## Passed

- Full target build for `Seeeduino:nrf52:xiaonRF52840Sense` using Arduino CLI 1.5.1, Seeed nRF52 Boards 1.1.13 and native Apple Silicon Arm GNU 13.2.Rel1 / GCC 13.2.1.
- Bundled libraries: Adafruit TinyUSB 1.7.0 and Servo 1.1.2. No separately installed Servo library is used.
- Target size: **50,224 bytes flash / 7,704 bytes global RAM**.
- Native Arduino ctags 5.8-arduino11 built from official source. The local cached source renames the reserved `__unused__` macro to avoid a collision with current macOS SDK headers. This cache is excluded from git.
- Host tests against the actual sketch: disarmed boot, explicit newline arming, exactly 1500 µs commands, one selected PWM output, timed power-off, serial disconnect shutdown, immediate stop, malformed/overlong input, timer rollover and PWM attachment failure.
- VS Code task JSON, Python syntax and whitespace checks.

The newer native linker prints warnings for unimplemented POSIX file-descriptor/syscall stubs in Newlib. The build succeeds; this sketch does not use those POSIX interfaces. The vendor UF2 conversion script also emits a Python regex-escape warning. Neither warning was suppressed.

## Hardware status

The connected USB device is identified as **Seeed XIAO nRF52840 Sense** (VID 2886 / application PID 8045). At upload, the user confirmed the battery was unplugged and both horns were off.

**Firmware upload confirmed:** after entering bootloader USB PID **0045**, the native Python uploader flashed the compiled DFU package and returned **`Device programmed.`**. A subsequent USB check received **`ROBOT SERVO CENTER 0.1`**, the command menu and **`OFF.`**. The verification sends only `help` and `off`, both disarming commands, and closes the serial connection afterward.

Bootloader mode was identified by USB enumeration; the user did not observe the expected pulsing red LED, so LED appearance alone was not used as the readiness check. An earlier attempt in application mode timed out. Adafruit-nrfutil can return process status zero despite a failed upload; the project upload script therefore requires its explicit positive acknowledgement.

The bundled Servo implementation was inspected: its 20 ms period is 50 Hz and its 8 µs duty resolution rounds a 1500 µs request down to approximately 1496 µs. Host tests check the requested value, not physical pulse timing.

No servo power-on command has been sent. No motor movement, PWM timing measurement, low-voltage cutoff test or mechanical fit test has been performed by the agent. Electrical measurements below were taken and reported by the user; the agent has no direct voltage telemetry. Host tests do not verify physical GPIO voltages or wiring.

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

The agent repeated the USB `help`/`off` check and received the expected version banner and `OFF.` acknowledgement. The reported 3.9 V resting VOUT stopped preparation for the timed power test; no `power`, `lower` or `upper` command has been sent. Another `help`/`off` check also received the expected acknowledgement. The subsequent explicit slide-position check shows that the mechanical switch changes the output voltage.

Pololu states that the [disabled output is disconnected and floating](https://forum.pololu.com/t/reverse-voltage-on-mini-mosfet-slide-switch-with-2810/11758). The guide's earlier expectation that OFF must measure near 0 V was too strict and has been corrected. The approximately 1.1 V OFF reading is compatible with a floating output, but its source/current capability has not been determined; no light-load resistor test was performed. **Timed software switch operation, shutdown under a known load, supply sag under servo load and servo centering remain unverified.** A supervised three-second `power` command with no PWM is next, after explicit meter readiness with the slide returned to OFF.

Re-run software checks with:

```sh
python3 scripts/robot.py test
python3 scripts/robot.py build
```
