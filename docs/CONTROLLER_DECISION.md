# Controller and IMU decision

The reference robot uses an **M5Stack ATOM Matrix**. It already contains an **MPU6886 six-axis IMU** (a 3-axis accelerometer and 3-axis gyroscope), and its Arduino firmware reads that sensor with `M5.IMU.getAccelData(...)` and `M5.IMU.getGyroData(...)`. The reference code drives the two servos from GPIO 26 and 32. The author's build uses a 3.7 V LiPo and reports that it worked without a boost converter, even though M5Stack's published ATOM Matrix input specification is 5 V. We should treat that as a successful experiment on that build, not proof of operation over every cell voltage and load. [Project article](https://homemadegarbage.com/rl13), [firmware](https://github.com/homemadegarbage/SelfRisingRobot/blob/main/Arduino/robo03/robo03.ino), [M5Stack specifications](https://docs.m5stack.com/en/core/Atom-Matrix).

Our selected **Seeed XIAO nRF52840 Sense** likewise puts the IMU **on the controller board itself**. The IMU is the **LSM6DS3TR-C**. The board also contains an nRF52840 processor, battery pads, a charger IC, and USB-C. The Sense board has a 21 × 17.8 mm footprint. The ordinary XIAO nRF52840 without “Sense” has **no IMU**; its smaller name difference matters. [Seeed's board comparison and pin map](https://wiki.seeedstudio.com/XIAO_BLE/).

**Exact purchase variant:** the linked [standard XIAO nRF52840 Sense, SKU 102010469](https://www.seeedstudio.com/Seeed-XIAO-BLE-Sense-nRF52840-p-5253.html). The [Sense Plus, SKU 102010694](https://www.seeedstudio.com/Seeed-Studio-XIAO-nRF52840-Sense-Plus-p-6360.html) keeps the same IMU and charger but exposes extra solder pads/GPIOs, which this two-servo robot does not need. It is a reasonable substitute only after checking the underside battery-pad layout and mount clearance. The [non-Sense XIAO nRF52840, SKU 102010448](https://www.seeedstudio.com/Seeed-XIAO-BLE-nRF52840-p-5201.html), has no IMU and is unsuitable without adding one.

## Where the IMU is in our robot

The XIAO Sense board is mounted rigidly inside the under-base enclosure. Its onboard LSM6DS3TR-C measures the **base's** accelerations and angular rates; there is no external IMU board or cable. Firmware combines those measurements to estimate gravity direction. The final board-to-base rotation is calibrated, and the simulator includes the relocated IMU site. [Enclosure layout](../cad/electronics_pod/README.md) · [Current simulation](../sim/enclosure_c3/upright/README.md).

```text
   On the base: XIAO nRF52840 Sense PCB
   ├── nRF52840 MCU       → runs the trained policy at 50 Hz
   ├── LSM6DS3TR-C IMU    → senses base motion (accel + gyro)
   ├── BQ25101 charger    → charges a standard 1S LiPo over USB-C
   ├── D8 and D7          → lower and upper servo PWM (7 Nov 2026 harness)
   └── BAT pads           → battery input

   Rev C power: battery → Pololu master switch → XIAO BAT+ and two servos
                all grounds share a negative bus
```

An accelerometer alone cannot reliably indicate gravity during a fast flip because it also sees movement acceleration. The controller uses a gyro/accelerometer gravity-direction filter with calibrated board-to-base alignment. The current C3 simulation runs the same portable observer and supervisor; dynamic accuracy still needs further physical characterization.

## Why select XIAO Sense for this version?

| Question | Reference ATOM Matrix | Selected XIAO nRF52840 Sense | Practical implication |
|---|---|---|---|
| Is the IMU onboard? | Yes, MPU6886. | Yes, LSM6DS3TR-C. | **No IMU component-count advantage** either way. |
| Board envelope | 24 × 24 × 13.8 mm, 7.3 g including its case. | 21 × 17.8 mm board footprint. | XIAO's footprint is about **35% smaller**; actual assembled robot footprint is currently set mostly by the battery, so this does not shrink the base by 35%. |
| Processor | ESP32 up to 240 MHz, with Wi-Fi. | Cortex-M4F at 64 MHz, with BLE. | Both can run a small policy; recorded XIAO inference is roughly 1.2 ms at a 50 Hz policy rate. ATOM has substantially more compute and an existing Wi-Fi interface. |
| Single-cell supply | Official input: 5 V. Author reports direct 3.7 V worked. | Dedicated 1S battery pads and onboard charging circuit. | XIAO provides a documented battery/charging arrangement without adding a boost converter. |
| Charging | Reference battery bundle includes external USB chargers. No onboard LiPo charger is listed in the ATOM Matrix specifications. | Onboard BQ25101 charger through USB-C at about 100 mA with firmware configuration. | XIAO allows in-robot charging without a separate charging board or unplugging the pack. The selected Rev C master-switch harness uses PWM-off charging; current and termination remain unmeasured. See [operating instructions](OPERATING_INSTRUCTIONS.md). |
| Development convenience | The reference firmware, button, 5×5 LED display and Wi-Fi web interface already exist. | Custom IMU, PWM, filter and policy firmware was required and is implemented. | **ATOM wins for reproducing the reference quickly.** XIAO is my choice for the smaller onboard-charge version. |

The XIAO is therefore **better for our selected battery and component-count goal**, not universally better. The reference ATOM is a valid fallback if replicating its firmware and Wi-Fi calibration UI matters more than the charging integration. Swapping controllers changes the mount, wiring and firmware, but not the basic two-joint robot concept. Do not assume an ATOM S3 or another XIAO version has the same IMU or power circuit without checking its exact SKU.

## How far can we reduce the parts count?

The minimum active hardware is **one XIAO Sense, two servos and one 1S battery**. A matching battery connector/pigtail and wires are still needed for a removable pack. The XIAO already supplies the processor, IMU, regulator and USB charger; it requires **no separate Raspberry Pi, IMU breakout, servo driver board, boost converter or charging board** for this design.

The installed **Rev C** adds one previously purchased Pololu 2810 LV as a manual battery master switch. It isolates battery power from both controller and servos when USB is absent. D2 and the switch's ON/SW pads are unused. No separate servo driver, charger, boost converter, capacitor or signal resistor was added. [Complete current wiring](../electrical/FROM_SCRATCH.md).

The [Rev B direct-power harness](../electrical/REV_B_NOTES.md) removed the switch temporarily; it is historical. Further integration of MCU, IMU, charging and power switching belongs to the [custom PCB idea](INTEGRATED_CONTROLLER_PCB.md).

Separately, the current **500 mAh battery** is the largest footprint driver. The reference uses a 220 mAh pack. A properly rated smaller cell could materially shrink the platform, but it will shorten runtime and must be checked for stall-current delivery, connector, 4.2 V charge chemistry and physical protection before redrawing the base.
