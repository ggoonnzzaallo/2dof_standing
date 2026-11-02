# Operating instructions

For the current Rev B wiring (no Pololu switch), XIAO nRF52840 Sense and recovery firmware **0.2**. Recovery with USB unplugged was confirmed on 2 November 2026.

The robot starts **disarmed after every reset or power cycle**. Arming briefly centers both joints, then starts the onboard recovery policy. Disconnecting USB or closing the terminal after successful arming leaves recovery running.

## Terminal setup

Open a terminal in the repository folder. On the current Mac:

```sh
cd "/Users/super23/Documents/BLDC Motor Build/2dof_standing"
```

The `./robot` command uses the project's installed Python environment; no environment activation or Arduino IDE is needed. If tools have not been installed on another computer, run `python3 scripts/robot.py setup` first.

## Disarm and turn off

**With USB connected:** support the robot and run:

```sh
./robot stop
```

Wait for **`OFF`** and the PWM-stopped confirmation. This stops control pulses; the servos still receive power and can draw idle current or retain holding torque.

**With USB unplugged:** disconnect the battery to turn the robot off.

For complete power-off or storage, disconnect **both battery and USB**. Removing the battery while USB remains connected does not guarantee that the servo supply is unpowered, because the XIAO charger feeds the shared battery bus.

## Check the battery and decide when to charge

Connect USB and run:

```sh
./robot status
```

This reads state without stopping or recentering a running controller. Reconnecting USB does not disarm it. Example:

```text
STANDALONE | BAT 3.850 V | frames 1234
```

| Reading | What to do |
| --- | --- |
| Around **4.2 V** | Near full charge. |
| Around **3.7 V** | Recharge before more testing. Arming requires at least 3.7 V. |
| Below **3.6 V during operation** | The firmware stops PWM after two consecutive low readings; disconnect the battery promptly. |

These readings are uncalibrated voltage estimates, not a battery percentage. Motion causes voltage sag, and connecting USB can raise the reading as charging begins. A USB-only reading with no battery attached is not a cell-voltage measurement. USB connected while the robot moves does not prove that the battery is gaining charge.

The firmware samples approximately every 100 ms. It also stops PWM on a single reading below **3.4 V** or above **4.4 V**; arming accepts only **3.7–4.4 V**. These guards cannot cut the direct servo supply or prevent a forgotten connected battery from continuing to drain.

**There is currently no low-battery warning light.** The proposed battery-status RGB LED remains a [future development idea](HARDWARE_BACKLOG.md). A stopped robot is not proof of low battery: sensor or timing faults can also stop it. With USB connected, `./robot status` reports the last stop reason; it does not automatically rearm.

## Charge through the XIAO USB-C port

1. If USB is connected, run `./robot stop` and wait for `OFF`.
2. Disconnect **USB and the battery** before changing connectors.
3. Unplug **both complete three-pin servo connectors**. Leave them disconnected throughout charging.
4. Reconnect the battery to its existing harness. It can stay physically mounted in the robot.
5. Connect USB-C to the Mac or a USB power supply. Charging starts through the XIAO's onboard charger; no terminal command or separate charger is needed.
6. Monitor charging while you are around. Disconnect USB and battery when finished if putting the robot away.

The uploaded firmware already selects approximately **100 mA** charging. For a depleted **500 mAh** battery, allow more than five hours: the ideal capacity/current calculation is five hours, with extra time for taper and board consumption. A partially discharged battery takes less time.

The board's separate **red charging LED** lights during charging and goes out when charging finishes or is inactive. An unlit LED alone does not prove a full battery; check for a reading near 4.2 V as well. This LED is separate from the proposed RGB battery-health indicator. See [Seeed's charging documentation](https://wiki.seeedstudio.com/XIAO_BLE/#battery-charging-current) and the [hardware charging details](../HARDWARE.md#battery-monitoring-and-charging).

Both servo plugs must be removed for routine charging: stopping PWM does not isolate their power, and the onboard charger is not a motor supply.

## Rearm after stopping or charging

1. Disconnect **USB and the battery**.
2. Reconnect both complete servo plugs, checking their orientation.
3. Reconnect the battery, then USB.
4. Place the robot upright with both links near straight, on a clear surface with room to move. Leave the base briefly still for the IMU to initialize.
5. Run:

   ```sh
   ./robot arm
   ```

6. Both joints briefly center, then the policy starts. Wait for **“Armed. Unplug USB”** before unplugging USB for battery operation.

If it is already connected and you only used `./robot stop`, leave the connections in place, put it near straight and run `./robot arm` again. Charge first if voltage is low; do not repeatedly rearm after a battery stop.

After a sensor, timing or battery fault, the controller stays stopped until explicitly rearmed. Resetting or cycling power also requires a new Mac arming command. With USB unplugged, disconnect the battery when testing is finished.

## VS Code and further details

The same commands are available through **Tasks → Run Task**:

- **Robot: arm for untethered use**
- **Robot: read state without stopping**
- **Robot: stop PWM**

Command records are saved under `build/arming/`. For firmware behavior, deployment records and limits, see the [recovery controller guide](../firmware/policy_control/README.md). For connector and bus wiring, see the [electrical guide](../electrical/README.md).
