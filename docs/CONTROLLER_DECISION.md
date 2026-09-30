# Controller and IMU decision

The reference robot uses an **M5Stack ATOM Matrix**. It already contains an **MPU6886 six-axis IMU** (a 3-axis accelerometer and 3-axis gyroscope), and its Arduino firmware reads that sensor with `M5.IMU.getAccelData(...)` and `M5.IMU.getGyroData(...)`. The reference code drives the two servos from GPIO 26 and 32. The author's build uses a 3.7 V LiPo and reports that it worked without a boost converter, even though M5Stack's published ATOM Matrix input specification is 5 V. We should treat that as a successful experiment on that build, not proof of operation over every cell voltage and load. [Project article](https://homemadegarbage.com/rl13), [firmware](https://github.com/homemadegarbage/SelfRisingRobot/blob/main/Arduino/robo03/robo03.ino), [M5Stack specifications](https://docs.m5stack.com/en/core/Atom-Matrix).

Our proposed **Seeed XIAO nRF52840 Sense** likewise puts the IMU **on the controller board itself**. The IMU is the **LSM6DS3TR-C**. The board also contains an nRF52840 processor, battery pads, a charger IC, and USB-C. The Sense board has a 21 × 17.8 mm footprint. The ordinary XIAO nRF52840 without “Sense” has **no IMU**; its smaller name difference matters. [Seeed's board comparison and pin map](https://wiki.seeedstudio.com/XIAO_BLE/).

## Where the IMU is in our robot

The XIAO Sense board is fastened rigidly **on the base platform**, at approximately `(x=23, y=18, z=6)` mm in `cad/assembly.step`. The IMU chip is soldered onto that board; it is not a separate breakout board or another BOM line. It measures the **base's** accelerations and angular rates. Firmware combines those measurements to estimate which way gravity points relative to the base. The policy uses that direction to decide how to move the arm. There is no external IMU cable. Record the final board orientation during assembly so the firmware can map chip axes to robot axes. A thick soft mount would let the board tilt separately from the base and corrupt the estimate.

```text
   On the base: XIAO nRF52840 Sense PCB
   ├── nRF52840 MCU       → runs the trained policy at 50 Hz
   ├── LSM6DS3TR-C IMU    → senses base motion (accel + gyro)
   ├── BQ25101 charger    → charges a standard 1S LiPo over USB-C
   ├── D0 and D1          → servo PWM signals
   └── BAT pads           → battery input

   Elsewhere: battery → servo-power switch → two servos
```

An accelerometer alone cannot reliably indicate gravity during a fast flip because it also sees movement acceleration. Firmware needs an attitude filter using the gyro and accelerometer, with a well-defined board-to-base axis mapping. The simulator's projected-gravity observation is currently idealized; `sim/README.md` calls out this remaining transfer step.

## Why select XIAO Sense for this version?

| Question | Reference ATOM Matrix | Proposed XIAO nRF52840 Sense | Practical implication |
|---|---|---|---|
| Is the IMU onboard? | Yes, MPU6886. | Yes, LSM6DS3TR-C. | **No IMU component-count advantage** either way. |
| Board envelope | 24 × 24 × 13.8 mm, 7.3 g including its case. | 21 × 17.8 mm board footprint. | XIAO's footprint is about **35% smaller**; actual assembled robot footprint is currently set mostly by the battery, so this does not shrink the base by 35%. |
| Processor | ESP32 up to 240 MHz, with Wi-Fi. | Cortex-M4F at 64 MHz, with BLE. | Both can plausibly run this small policy; on-device timing still needs measurement. ATOM has substantially more compute and an existing Wi-Fi interface. |
| Single-cell supply | Official input: 5 V. Author reports direct 3.7 V worked. | Dedicated 1S battery pads and onboard charging circuit. | XIAO provides a documented battery/charging arrangement without adding a boost converter. |
| Charging | Reference battery bundle includes external USB chargers. No onboard LiPo charger is listed in the ATOM Matrix specifications. | Onboard BQ25101 charger through USB-C. | XIAO removes the need to buy and carry a separate charger for the selected standard 1S cell. It charges slowly; see `HARDWARE.md`. |
| Development convenience | The reference firmware, button, 5×5 LED display and Wi-Fi web interface already exist. | New IMU, PWM, filter and policy firmware must be written. | **ATOM wins for reproducing the reference quickly.** XIAO is my choice for the smaller onboard-charge version. |

The XIAO is therefore **better for our selected battery and component-count goal**, not universally better. The reference ATOM is a valid fallback if replicating its firmware and Wi-Fi calibration UI matters more than the charging integration. Swapping controllers changes the mount, wiring and firmware, but not the basic two-joint robot concept. Do not assume an ATOM S3 or another XIAO version has the same IMU or power circuit without checking its exact SKU.

## How far can we reduce the parts count?

The minimum active hardware is **one XIAO Sense, two servos and one 1S battery**. A matching battery connector/pigtail and wires are still needed for a removable pack. The XIAO already supplies the processor, IMU, regulator and USB charger; it requires **no separate Raspberry Pi, IMU breakout, servo driver board, boost converter or charging board** for this design.

The recommended Rev A BOM adds **one Pololu servo-power switch** to the minimum active hardware. The capacitor and two signal resistors are optional troubleshooting parts, not necessary purchases for the first build:

| Item | Why consider it | If omitted |
|---|---|---|
| Servo-power switch — **included** | MCU can turn servo power off on a low-battery fault and while charging/programming. | Servos remain connected whenever the battery is plugged in. The pack must be unplugged for a true shutdown; USB charging needs careful testing with the permanently attached servo rail. |
| 1000 µF capacitor — **optional** | Buffers brief servo-current spikes near the load. | Start without it; add if loaded voltage measurements show dips/spikes or the MCU resets despite short, sound wiring. |
| Two 1 kΩ resistors — **optional** | Limit current that could enter unpowered servo signal inputs. | Use correct firmware power sequencing and verify with the actual servos. Add only if back-powering is observed. |

I recommend **retaining the switch for the first build**. It is the one added board that allows the firmware to cut motor power. Wire the servo signals directly for now and measure supply behavior under load. A simple mechanical slide switch may be smaller/cheaper, but it gives up firmware-controlled shutdown. Those are design choices, not one-for-one substitutions.

Separately, the current **500 mAh battery** is the largest footprint driver. The reference uses a 220 mAh pack. A properly rated smaller cell could materially shrink the platform, but it will shorten runtime and must be checked for stall-current delivery, connector, 4.2 V charge chemistry and physical protection before redrawing the base.
