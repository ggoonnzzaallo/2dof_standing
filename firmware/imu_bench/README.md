# Sensor commissioning before robot control

Prepared 1 November 2026. This sketch is for the classic XIAO nRF52840 Sense with its onboard LSM6DS3TR-C. It uses the installed non-mbed Seeed nRF52 1.1.13 core and its internal `Wire1` bus. No new wiring or sensor library is needed. The normal `upload` command still installs the existing servo bench program; `upload-imu` explicitly selects this sensor-only program.

## First upload and recording

1. Unplug battery and USB, then unplug both complete three-pin servo plugs. Connect the XIAO to the Mac by USB. The board should remain firmly mounted to the base for orientation measurements. Its BAT charger bus can power connected servos even with the battery removed.
2. From the repository root:

   ```sh
   python3 scripts/robot.py build-imu
   python3 scripts/robot.py ports
   python3 scripts/robot.py upload-imu
   .tools/arduino/python/bin/python scripts/imu.py \
     --seconds 10 --label upright --out build/imu/upright.csv
   ```

   Codex can run these commands once the physical setup is confirmed. Use a new filename for each recording; existing recordings are preserved.
3. For the first capture, keep the base flat and still. The recorder checks the firmware banner and `IMU_READY: 1` before starting a stream. It sends only `off`, `status`, `stream` and stop commands. It saves CSV plus a JSON summary in the ignored `build/` directory.
4. Review raw axes, approximate 1 g acceleration norm, near-zero stationary gyro, sample age, saturation and I2C error counts. A reported battery voltage with the battery unplugged is the charger/BAT node, not evidence of an attached cell.

The program holds D0/D1 LOW and contains no PWM, servo or policy calls. `off` stops sensor streaming; it does not disconnect battery power. USB disconnection also stops streaming. A stream is limited to 30 seconds; the recorder accepts captures up to 25 seconds.

## Sensor contract

- Read the hardware identity at candidate I2C addresses 0x6A/0x6B; require LSM6DS3TR-C `WHO_AM_I = 0x6A`. A different device fails rather than silently selecting another chip's scaling.
- Reset/configure the sensor, enable block data update and register auto-increment, and read back the configuration.
- Accelerometer and gyro run at 208 Hz in high-performance mode, with nominal ranges ±8 g / ±2000 deg/s. Scale factors are 0.244 mg/count and 70 mdps/count. CSV gyro units are **rad/s**. Firmware polls the ready flags and reads a new complete gyro/acceleration block; telemetry is approximately 50 Hz without a FIFO.
- All vectors are in **sensor axes**. At rest the accelerometer measures supporting specific force; an approximate sensor-frame DOWN vector is the negative normalized acceleration. During acceleration/impacts that is not a gravity estimate. No base-axis rotation, gyro bias correction or dynamic attitude filter is applied yet.
- `age_us` is the time since the completed sensor read; `t_us` is that read's MCU timestamp. It is not an exact sensor exposure timestamp. A sample older than 100 ms stops streaming. The recorder reports gaps, duplicates and saturation.
- Battery conversion is the existing eight-sample, uncalibrated ADC estimate. Charger configuration remains approximately 100 mA and the divider-enable pin remains LOW.

Sources: [Seeed's IMU guide](https://wiki.seeedstudio.com/XIAO-BLE-Sense-IMU-Usage/), the installed board's `variant.h`/`variant.cpp` pin mapping, and [ST's LSM6DS3TR-C datasheet](https://www.st.com/resource/en/datasheet/lsm6ds3tr-c.pdf), register descriptions and sensitivity table. Arduino pin 15 powers the internal IMU, and `Wire1` uses Arduino pins 17/16; these are internal board connections, not additional harness wires.

## Deployment sequence

1. **Read real sensor data:** confirm chip identity, units, timing, stationary noise and saturation.
2. **Map sensor axes to robot axes:** record known upright, side and inverted base orientations; estimate gyro bias while stationary. Verify rotation signs through slow manual rotations. A single upright pose cannot determine the complete mounting rotation.
3. **Calibrate actuators:** record each joint's PWM zero, angle direction, accessible endpoints and loaded response. Reuse the existing supported bench tests; no automatic full-range sweep is planned.
4. **Shadow the policy:** integrate the attitude estimator, run the same estimator in simulation, and time/check the exported actor on the XIAO while logging actions with servo outputs disabled. Retrain if the measured dynamics or observation model materially changes.
5. **Enable supervised recovery:** apply measured joint limits, battery/fault handling and explicit arming; compare real trajectories with simulation. The current simulation actor is not enabled by this diagnostic.

The pinned core's `Wire1` implementation contains hardware-event wait loops without a configurable timeout. This diagnostic has no active motor outputs; it does not establish recovery from an electrical bus hang. A bounded I2C transport or independently verified watchdog/fault strategy is required before using this sensor path for motor control.

## Checks

`python3 scripts/robot.py test` includes the actual sensor header/sketch compiled against fake GPIO/I2C, covering identity, register configuration, signed decode, scaling, partial reads, stale samples, stream timeout and serial disconnect. Logger checks cover static DOWN sign, timestamp rollover, stationary/moving data, saturation, error counts and sample gaps. These tests do not establish physical connectivity, mounting orientation, timing or accuracy.

The native XIAO build succeeds with 53,428 bytes of program storage and 7,960 bytes of static RAM. See [build_validation.json](build_validation.json) for source/image hashes and the distinction between compile checks and actual device observations.
