# Onboard recovery controller

**Release 0.9, deployed 7 November 2026.** Runs the C3 PPO actor at **50 Hz**, with **±90° targets**, varied recovery retries and smooth neutral holding on a level base. Lower PWM is **D8 / 8**, upper **D7 / 7**. [Model and results](../../sim/enclosure_c3/upright/README.md) · [deployment record](results/2026-11-07/deployment_0_9.json).

Use [operating instructions](../../docs/OPERATING_INSTRUCTIONS.md) to run, stop, charge or wake the robot. Use [firmware setup](../README.md) to install the toolchain and upload. Dated releases and physical trials are in [development history](HISTORY.md), not mixed into this guide.

## Runtime contract

| Item | Current behavior |
|---|---|
| Actor | 10 → 64 → 64 → 2; 4,994 float32 parameters |
| Observations | Base DOWN vector; gyro / 10; commanded targets / 90°; previous applied actions |
| Recovery output | Clipped increments up to 0.10 rad per 20 ms tick, bounded to ±90°; maximum target rate 5 rad/s |
| Servo mapping | `1500 - 509.295817894 * angle_rad`, approximately 700–2300 µs |
| Level-base mode | After about 0.2 s level/slow, ease both targets to zero at ≤2 rad/s and hold; tilt/spin restores recovery |
| Stalled attempts | Supervisor varies sweep signs, joint order, amplitude and timing; no online weight learning |
| Identity checks | Build verifies actor/model/runtime hashes; live arming requires matching firmware and fingerprints |

The IMU is on the base. The servos provide no position telemetry: commanded targets are not measured shaft angles. The pulse mapping extrapolates [visual zero/±45° calibration](../servo_calibration/results/2026-11-02/visual_mapping.json). A sampled C3 clearance audit supports ±90° on both; lower ±110° intersects the base. [Range calculations and limits](../../sim/enclosure_c3/upright/README.md#calculated-travel-clearance).

## Modes and stops

- **Battery-only startup:** wait at least two seconds for fresh sensors, hold nominal neutral for one second, then enter STANDALONE. USB power at startup selects CHARGE with PWM off instead.
- **STANDALONE:** no host heartbeat or fixed trial duration. Connecting USB to an already-running robot does not stop it.
- **CHARGE (5):** latched PWM-off mode; USB removal alone does not restart motion. This state does not verify charging current or a full cell.
- **INACTIVE (6):** 60 seconds without meaningful base-IMU movement detaches PWM and locks motion until MCU reset. Charge remains available. No serial command clears this lock.
- **Faults:** stale/invalid IMU data (20 ms), deadline lateness ≥10 ms, invalid numerical state, failed PWM attachment or invalid input stop PWM. Faults do not automatically rearm.

Arming requires an estimated BAT voltage of **3.7–4.4 V**. During operation, sampling every 100 ms stops PWM on two readings below 3.6 V, one below 3.4 V or one above 4.4 V. This does not measure current or brief brownout transients. PWM-off leaves idle loads powered; for storage, unplug USB and slide the master switch OFF. See [battery and charging instructions](../../docs/OPERATING_INSTRUCTIONS.md).

## No-motion recording

With battery and both complete servo plugs disconnected, connect USB and leave the base still for filter initialization. After [building/uploading the controller](../README.md):

```sh
.tools/arduino/python/bin/python scripts/control.py --shadow --seconds 10 --out build/control/shadow_01.json
```

Run commands from the repository root and use a new output filename per capture. Shadow runs the observer, actor and target integration without attaching PWM; both PWM fields must stay zero. The host records CSV/raw text, checks actor agreement and integration, then sends stop.

## Supervised motion trial

Unplug USB, reconnect battery and servo plugs, then reconnect USB. Start upright, links near straight, with clearance and cable slack. Arming commands nominal 1500 µs without position feedback.

```sh
.tools/arduino/python/bin/python scripts/control.py --seconds 15 --out build/control/upright_01.json
```

This moves the robot. The XIAO chooses actions; the Mac sends heartbeat/stop and records telemetry. Ctrl+C requests stop. The helper accepts 1–45 seconds; firmware independently limits supervised runs to 60 seconds and stops on USB loss or a missing three-second heartbeat. It does not automatically rearm after a fault. Do not open a second serial monitor during a trial.

For untethered operation, `./robot arm` verifies a standalone handoff; `./robot stop`, `./robot charge` and `./robot status` provide the everyday Mac controls described in the [operating guide](../../docs/OPERATING_INSTRUCTIONS.md#optional-mac-controls).

## Telemetry and offline analysis

Rows use a fixed nonblocking buffer; `dropped` counts rows skipped when the USB FIFO is full. The actor still evaluates every policy tick. The host stops a supervised trial if no rows arrive for 500 ms. `_u6` fields multiply dimensionless values by 1,000,000; `_urad` fields encode radians × 1,000,000. PWM fields are commands, not shaft measurements.

The `override` flag identifies neutral-hold or retry actions. Actor parity applies to non-overridden rows; history, target and PWM bounds are checked on every row. Offline analysis sends no device commands:

```sh
.tools/arduino/python/bin/python scripts/control.py --shadow --analyze build/control/shadow_01.csv
.tools/arduino/python/bin/python scripts/control.py --analyze build/control/upright_01.csv
```

Historical captures may need their matching `--actor-header`, `--increment .06` and `--limit-deg 80`.

Raw serial uses 115200 baud. `state` is non-stopping (`./robot status` uses it); raw `status`/`help` stop active motion before printing, while preserving CHARGE/INACTIVE. `keep` refreshes an existing supervised session; `off`/`!` stop PWM. Reconnecting serial or an unknown command never starts control.

## Evidence

Release 0.9 passed actual-sketch tests, portable supervisor checks and 13 Mac-helper tests. Export parity error was at most 4.77e-7 over 1,000 vectors; native build used 90,284 bytes flash / 8,000 bytes static RAM. The uploader acknowledged programming and standalone frames advanced. Physical 0.9 recovery and straight-hold accuracy await operator confirmation.

[Training, held-out evaluation and geometry limits](../../sim/enclosure_c3/upright/README.md) · [manifest](PolicyManifest.json) · [controller history](HISTORY.md) · [validation log](../VALIDATION.md) · [documentation index](../../docs/README.md).
