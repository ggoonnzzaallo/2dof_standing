# XIAO actor arithmetic probe

This separate sketch compiles the saved simulation actor for the classic XIAO nRF52840 Sense. It has no IMU estimator and generates no servo PWM. It is not the self-righting robot controller.

From the repository root:

```sh
python3 scripts/robot.py build-probe
```

The normal `build` and `upload` commands still use `servo_center`; `build-probe` only compiles into the ignored `build/policy_probe/` directory. No probe upload command is added. No firmware was uploaded during the simulation experiments or compile check.

The probe includes the committed [actor header](../../sim/recovery/results/policy_simulation_only.h), holds D0 and D1 LOW, and preserves the existing approximately 100 mA charging configuration. With Rev B wiring, LOW signal pins do not disconnect servo power. For any future upload or arithmetic test, unplug the complete removable servo plugs before connecting USB; the shared battery/charger bus can otherwise power them.

After a future upload, serial `probe` at 115200 baud evaluates a fixed upright observation, then reports mean/max inference time over 200 calls with varying inputs and a checksum. These are synthetic observations. No action is converted into a servo command. Real MCU timing remains unmeasured until that test is run on the board.

The [policy contract](../../sim/recovery/results/policy_contract.json) records the observation/action mapping. Sensor alignment, estimation, servo signs/limits and loaded dynamics still need calibration before this actor can control the robot.

The [build record](build_validation.json) reports **69,968 bytes of program storage** (69,976 including the exception-index table) and **7,464 bytes of static RAM** for this probe. Runtime heap/stack high-water use and board inference time have not been measured. The build emits existing toolchain warnings for unused POSIX syscall stubs and a Python escape sequence; these are recorded alongside the image/source hashes.
