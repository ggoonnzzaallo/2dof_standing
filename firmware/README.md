# Firmware setup

The installed robot uses [controller 0.9](policy_control/README.md) with the [Rev C master-switch harness](../electrical/FROM_SCRATCH.md): lower servo **D8 / 8**, upper **D7 / 7**. For everyday running and charging, use the [operating instructions](../docs/OPERATING_INSTRUCTIONS.md); a computer is optional.

## Set up the Mac toolchain

From the repository root, with Python 3.12+, macOS Command Line Tools and network access:

```sh
python3 scripts/robot.py setup
```

No Arduino IDE or VS Code extension is required. Setup pins Arduino CLI 1.5.1 and Seeed's regular/non-mbed nRF52 Boards 1.1.13; Apple Silicon uses native Arm GNU 13.2.Rel1. Downloads stay in ignored `.tools/`, compiled firmware in ignored `build/`. VS Code's **Terminal → Run Task → Robot: …** exposes the same workflows.

## Build and upload the recovery controller

For USB-only programming, disconnect the battery and both complete three-pin servo plugs, then connect USB. Battery removal alone does not isolate the shared servo bus from the charger.

```sh
python3 scripts/robot.py build-control
python3 scripts/robot.py ports
python3 scripts/robot.py upload-control
./robot status
```

Upload requires a recognized XIAO nRF52840 Sense and the uploader's `Device programmed.` acknowledgement. If the bootloader is unreachable, double-press reset, list ports and retry. Use the [controller guide](policy_control/README.md) for shadow recording and live trials.

**Plain `build` / `upload` select the historical servo bench, not recovery.** Use the `-control` commands above for this robot.

## Other firmware and records

- [Current controller](policy_control/README.md): modes, runtime contract, telemetry and fault handling.
- [Historical servo/dance guide](BENCH_GUIDE.md): bench commands and the old direct-power harness.
- [IMU commissioning](imu_bench/README.md), [servo calibration](servo_calibration/README.md), [policy shadow](policy_shadow/README.md), [arithmetic probe](policy_probe/README.md): separate explicit build/upload targets.
- [Controller history](policy_control/HISTORY.md) and [validation log](VALIDATION.md): dated evidence, not current operating procedures.

[All documentation](../docs/README.md)
