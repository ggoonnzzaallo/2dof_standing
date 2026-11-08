# Operating instructions

**V1, updated 7 November 2026 — controller 0.9.** One Pololu battery master switch; lower signal **D8 / 8**, upper **D7 / 7**. Normal running and charging do not require a computer. [Wiring](../electrical/FROM_SCRATCH.md) · [Current deployment evidence](../firmware/policy_control/results/2026-11-07/deployment_0_9.json).

Controller 0.9 uses **±90° targets**. On a slowly moving level base it eases both targets to calibrated neutral (1500 µs) at <=2 rad/s and holds a straight arm. It switches back to recovery when tilted or rotated quickly. Varied stalled-recovery sweeps remain. This commands neutral without shaft-position readback; physical accuracy depends on horn calibration and load. The 60-second inactivity shutdown still applies. [Controller and range checks](../sim/enclosure_c3/upright/README.md).

## Run without a computer

1. **Unplug USB** and slide the Pololu **OFF** to remove all robot power.
2. Place the base on a clear surface, with the links near straight and room for the trained ±90° motion. Switching ON will move the robot.
3. Slide **ON**. Keep the base still while the IMU initializes.
4. After about **two seconds**, both joints are commanded to nominal neutral (1500 µs) for **one second**, then onboard recovery starts automatically. No Mac command or heartbeat is required.

Startup requires fresh IMU/filter data and an estimated BAT voltage of **3.7–4.4 V**. If the IMU cannot initialize within 15 seconds, or a battery/sensor/PWM fault occurs, motion remains off; startup does not keep retrying. Correct the cause before another power cycle. Turning the Pololu OFF while USB is still attached does not fully power down the XIAO.

## Automatic inactivity stop

While recovery runs, **60 seconds without meaningful movement at the base IMU stops PWM and locks motion until reboot**. Moving the robot, reconnecting USB or sending arm commands does not clear it. Status reports **INACTIVE / REBOOT REQUIRED**, mode **6**.

To wake without a computer: **unplug USB, slide OFF, then ON**. Automatic startup repeats. Pressing the XIAO reset button once also restarts it: without USB it auto-starts; with USB it selects charge mode.

The timer starts when recovery starts and resets on base motion. Joint motion alone does not count: the IMU is on the base. Initial noise thresholds are three consecutive fresh samples with gyro magnitude ≥0.08 rad/s (about 4.6°/s), or acceleration-vector change ≥0.04 g relative to the last motion reference. Gradual tilts can accumulate. Running-servo vibration could reset the timer and still needs observation in use. The same guard runs in no-PWM shadow mode for verification.

The lock survives `stop`, `charge`, USB serial reopening and all motion commands. Charging remains available while locked. Only an actual MCU reset clears the lock.

## Charge without a computer

1. Start with **USB unplugged and slider OFF**.
2. Connect USB-C to the Mac or a USB supply. USB power at startup automatically selects **CHARGE / PWM OFF**, mode **5**, even without a serial connection.
3. Slide **ON** so the battery is connected to the XIAO charger. Leave **ON + USB** while charging. No command is needed.
4. After charging, **unplug USB and slide OFF** for storage. To run, slide ON again with USB absent. Unplugging USB alone leaves charge mode motionless until reboot or an explicit bench arm command.

**Connecting USB to an already-running robot does not itself stop motion.** For immediate charging without a computer, fully power down first and follow the sequence above. Alternatively, leave the base still for the inactivity timeout, or use `./robot charge` from the Mac.

The charger operates whenever USB and battery are electrically connected. Charge mode stops PWM; it does not measure charging current or a full cell. The approximately **100 mA** setting is unchanged. Servo idle current and the switch LED reduce current available to the battery; movement can exceed charger output and discharge it despite USB. A depleted 500 mAh pack can take more than five hours, depending on idle load and taper.

Through-switch battery current, servo idle consumption and complete-cycle termination are **not yet measured**. The red charger LED indicates activity, not guaranteed net battery charging or precise charge level. These are remaining characterization limits, not features a firmware state can verify. See [electrical checks](../electrical/README.md#commissioning-the-new-harness).

## Stop and store

For full OFF, **unplug USB and slide the Pololu OFF**. No internal connector access is needed for normal operation. Before soldering or servicing, disconnect battery and USB completely.

Inactivity, faults, `stop` and `charge` detach PWM and drive D8/D7 LOW, but **leave the XIAO and servo idle loads powered**. They are not electrical isolation or deep sleep. Do not use software stop as long-term battery storage.

With USB connected and the switch OFF, the battery is isolated and cannot charge; USB may still power the XIAO/shared servo rail through the charger. This is neither full OFF nor a way to restart battery-only recovery.

## Optional Mac controls

From this repository folder:

```sh
./robot status   # Read state without stopping or recentering
./robot stop     # Stop PWM and cancel pending automatic startup
./robot charge   # Latch PWM-off charge mode; retains any inactivity lock
./robot arm      # Centre joints, then start recovery; refuses an inactivity lock
```

For explicit bench arming, connect USB, place the robot near straight with clearance, then run `./robot arm`. It confirms standalone operation; USB may then be removed. A charge-mode boot does not prevent this explicit override, unless inactivity has locked motion. You do not need this procedure for everyday battery-only startup.

The helper uses the installed project Python. On another Mac, run `python3 scripts/robot.py setup` first. Records go to `build/arming/`; matching VS Code tasks are available. [Firmware setup](../firmware/README.md).

## Battery and fault checks

With the switch ON, `./robot status` reports approximate BAT voltage. Load, charging and wiring affect it; with the switch OFF it is the isolated BAT/charger node, **not the cell**. There is no current sensor or precise battery-percentage estimate.

| Reading with switch ON | Meaning/action |
|---|---|
| Around 4.2 V | Near full; verify charge completion separately. |
| Around 3.7 V | Recharge before further testing; startup/arming require at least 3.7 V. |
| Below 3.6 V for two consecutive samples | PWM stops; unplug USB and slide OFF promptly. |
| One sample below 3.4 V or above 4.4 V | Immediate PWM stop. |

Voltage is sampled about every 100 ms. The guard cannot operate the physical slider. A forgotten ON robot can discharge its pack after motion stops. Do not repeatedly reboot/rearm a low battery. `status` also reports the last stop reason; sensor/timing/numerical faults stop motion rather than automatically restarting it.

The current [upright C3 actor/runtime](../sim/enclosure_c3/upright/README.md) uses ±90° targets and a 5 rad/s target-rate cap. Earlier C2 and first-C3 experiments remain historical. Optional next-iteration ideas are in the [hardware backlog](HARDWARE_BACKLOG.md).
