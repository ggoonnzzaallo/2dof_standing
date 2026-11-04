# Operating instructions

**Rev C instructions, prepared 3 November 2026:** one Pololu battery master switch and controller firmware **0.3**. The enclosure and software are prepared, but wiring is not yet installed and firmware is not uploaded. Complete the [wiring and commissioning checks](../electrical/README.md) first.

**Until the rewire:** the last confirmed Rev B hardware still needs battery **and USB unplugged** for full OFF, and both complete servo plugs unplugged for routine charging. The uploaded firmware remains 0.2; the new `charge` command needs 0.3. Existing arm/stop/status commands remain compatible with 0.2.

## Terminal

```sh
cd "/Users/super23/Documents/BLDC Motor Build/2dof_standing"
./robot status   # Read state without stopping or recentering
./robot stop     # Stop PWM; power remains connected
./robot charge   # Firmware 0.3: latch PWM-off charging mode
./robot arm      # Centre both joints, then start onboard recovery
```

The helper uses the installed project Python; no Arduino IDE or environment activation is needed. On a new Mac, install tools using `python3 scripts/robot.py setup` first. Records are saved in `build/arming/`. VS Code has matching arm, status, stop and **Robot: charge mode (PWM off)** tasks.

## Stop and store

Support the arm and run **`./robot stop`** with USB connected. Wait for OFF confirmation. This detaches PWM and drives D0/D1 LOW, but does not physically cut servo power or idle drain.

For complete Rev C OFF, **unplug USB and slide the Pololu OFF**. No battery connector needs reaching. The robot boots disarmed after every reset or power cycle and never automatically rearms after a fault.

With USB connected, OFF disconnects the cell but USB may still power the XIAO and shared servo rail through the charger. Therefore OFF + USB is neither full OFF nor battery charging. Before soldering or servicing, unplug the battery **and** USB rather than relying on the switch alone.

## Charge

1. Support the links so they can relax when PWM stops. Leave the battery and servo connectors connected inside the enclosure.
2. Slide **ON** and connect USB-C to the Mac. Connecting USB alone does not stop an already-running policy.
3. Run **`./robot charge`** and wait for **CHARGE / PWM OFF**, device mode **5**.
4. Keep **ON + USB** while charging. Both PWM outputs remain detached and LOW; the servos remain electrically powered. Closing the terminal, reading status or losing USB serial does not resume motion. You may transfer the cable to a USB supply while leaving the switch ON; a reset instead boots disarmed with PWM off.
5. After charging, **unplug USB and slide OFF** for storage. To run again, leave ON, connect the Mac and explicitly arm.

The charger starts automatically when USB and battery are electrically connected. `charge` stops motion; it does not enable the charger hardware, measure charging current or indicate a full cell. The approximately **100 mA** setting is unchanged. Servo idle current and the switch LED leave less current for the cell; movement can exceed charger output and discharge it despite USB. More than five hours may be needed for a depleted 500 mAh pack, depending on idle load and taper.

**Before treating this as validated charging, measure through-switch battery current, no-PWM servo consumption and complete-cycle termination with the new harness.** The board's red charge LED indicates charger activity, not guaranteed net battery charging. Idle load may affect termination/LED behavior. No connector access or extra charger is part of the selected workflow; if idle load prevents completion, the design needs reconsideration rather than a software claim of success. See [complete wiring](../electrical/FROM_SCRATCH.md), [electrical checks](../electrical/README.md#commissioning-the-new-harness) and [TI charger limitations](https://www.ti.com/product/BQ25101).

## Battery checks

With switch **ON**, connect USB and run `./robot status`. It does not stop a running policy or exit charging mode. Voltage is approximate and affected by load, charger output and wiring. With the switch OFF, the ADC reads the isolated BAT/charger node, **not the cell**. There is no current sensor, switch-position sensor or battery-percentage measurement.

| Reading with switch ON | Action |
|---|---|
| Around 4.2 V | Near full; verify charge completion rather than relying on voltage alone. |
| Around 3.7 V | Recharge before further testing. Arming requires at least 3.7 V. |
| Below 3.6 V during operation | PWM stops after two consecutive readings; unplug USB and slide OFF promptly. |

Sampling is about every 100 ms. One reading below 3.4 V or above 4.4 V also stops PWM; arming accepts 3.7–4.4 V. The guard cannot turn the physical slider OFF. A forgotten ON robot can continue draining its pack after a software stop. The battery-status RGB light remains a [future idea](HARDWARE_BACKLOG.md); it is separate from the charger LED.

## Arm and recover

1. Leave the internal battery/servo connectors connected; slide **ON** and connect USB.
2. Put the robot upright, links near straight, on a clear surface with room to move. Keep the base briefly still for the IMU.
3. Run **`./robot arm`**. Both joints briefly centre at nominal 1500 µs, then onboard recovery starts. This moves the robot.
4. Wait for **Armed. Unplug USB** before removing the cable. Standalone recovery continues on battery; reconnect USB for stop, charge or status commands.
5. At the end, unplug USB and slide OFF. After a fault, check the reported reason and explicitly rearm only after resolving it; do not repeatedly rearm a low battery.

The existing ±80° policy and timing/battery/sensor guards are unchanged. The user has approved the new enclosure fit. The [revised offline model](../sim/enclosure/README.md) now includes its floor contacts, slicer masses and relocated IMU; physical recovery needs supervised evaluation of a new candidate after retraining. See the [controller guide](../firmware/policy_control/README.md) and [enclosure fit instructions](../cad/electronics_pod/PRINT_FIT_CHECK.md).
