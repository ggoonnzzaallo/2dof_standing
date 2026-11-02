# Hardware and commissioning

**Future revision:** the user requests a custom carrier PCB to reduce loose wiring. Track this in [the hardware backlog](docs/HARDWARE_BACKLOG.md). Wiring mass is explicitly excluded from the first mass model at the user's request.

**Hardware status (2 November 2026):** The PTK 7465 MG pair is assembled with horns installed and Rev B direct-battery wiring live. Both joints have been cycled and visually checked at nominal straight (1500 µs) and approximately ±45° (1100/1900 µs). The [reviewed static mapping](firmware/servo_calibration/results/2026-11-02/visual_mapping.json) identifies negative pulse-to-CAD-angle signs for both joints. Full travel, compound clearance, loaded dynamics and power margin remain unmeasured. See [procurement status](docs/PROCUREMENT_STATUS.md).

The IMU is the LSM6DS3TR-C chip **on the XIAO nRF52840 Sense PCB**. Mount that PCB rigidly on the base, near the controller envelope shown in `cad/assembly.step`. There is no separate IMU module or IMU wire harness. The reference ATOM Matrix also contains its own IMU (MPU6886). See the [board comparison and parts-count options](docs/CONTROLLER_DECISION.md).

## What the robot can measure

| Device | Available to the XIAO | Role |
|---|---|---|
| **One** onboard LSM6DS3TR-C IMU | Three-axis acceleration and three-axis angular velocity | Estimate base orientation relative to gravity and its rotation rate. Six axes means two three-axis measurements, **not six IMUs**. The IMU is rigidly attached to the base, so it does not directly measure either moving link. [Seeed IMU guide](https://wiki.seeedstudio.com/XIAO-BLE-Sense-IMU-Usage/). |
| XIAO battery-voltage ADC divider | Cell voltage after calibration | Low-battery protection and optional policy input; not a joint or contact sensor. See battery-monitoring details below. |
| Two PTK 7465 MG servos | Commanded PWM targets only | The selected three-wire servos expose signal, power and ground, with no shaft-angle, velocity, load, current or battery-voltage telemetry to the XIAO. They control their own position internally. [PTK's related 7465 MG-D page](https://www.ptkhobby.com/en/sys-pd/234.html). |
| XIAO Sense onboard microphone | Present but unused | It is not required for upright recovery or the current policy. [Seeed board specification](https://wiki.seeedstudio.com/XIAO_BLE/). |

This sensor set is enough to **attempt** the current ten-input policy because its inputs are base gravity direction and angular rate, the last two commanded joint targets and the previous two actions; actual joint angles and contact state are deliberately excluded. It is not full-state feedback. A stalled, back-driven or lagging servo can be far from its commanded target without the controller knowing. If measured recovery trials show this matters, the first sensor upgrade should be two joint-position feedback channels or servos that expose angle telemetry, rather than a second base IMU. Such a change also requires updating the policy observation and training model.

If command-only observations prove insufficient after physical trials, joint feedback would require a different servo or carefully characterized modification. That would change the wiring, observation vector, model and CAD. It is not part of the ordered Rev A hardware; see [servo tradeoffs](docs/SERVO_DECISION.md).

## Power and signals

**Current electrical revision: Rev B (30 October 2026), direct battery power with no Pololu switch.** See the [complete schematic](electrical/REV_B_WIRING.pdf) and [wiring/operating guide](electrical/README.md). The previously purchased switch is unused; earlier Rev A tests remain historical records.

```text
1S battery / removable RCY connector
  + ---- J1 VBAT+ bus ----+---- XIAO BAT+
                         +---- lower servo + (existing 3-pin plug)
                         +---- upper servo + (existing 3-pin plug)
  - ---- J2 GND bus ------+---- XIAO BAT- or GND
                         +---- lower servo GND
                         +---- upper servo GND
XIAO D0 ---------------------- lower servo signal
XIAO D1 ---------------------- upper servo signal
XIAO D2 ---------------------- UNUSED / no wire
USB-C ------------------------ XIAO programming + onboard charging
```

There are **two four-way physical buses and two PWM wires**. Servo running current comes directly from the battery-side junctions, not through the XIAO regulator, BAT pad or PCB traces. Keep one small branch from J1 to BAT+ and one from J2 to XIAO ground. Insulate J1 and J2 separately; keep the existing three-pin servo plugs removable. Never connect servo power to XIAO 3V3 or 5V/VBUS. No replacement switch, connector, external IMU, PWM board, booster, capacitor or resistor is required.

**Manual full OFF is battery AND USB disconnected.** During battery-only operation, unplugging the battery turns the robot off. USB can also feed the shared BAT+ node through the onboard charger, so removing only the battery while USB remains connected does not guarantee servo power isolation. For USB programming and routine charging, unplug both complete three-pin servo plugs. For supervised terminal motor tests, connect the battery before USB and keep the arm supported; this is not unattended charge mode. Stop PWM before changing connectors, with both power sources unplugged during rewiring.

The firmware's `off`, emergency stop, timeout and serial disconnect stop PWM; they **cannot disconnect the direct servo supply**. A servo may retain holding torque or draw idle current without new pulses. Keep the harness short and secure, and add passive components only if measured behavior justifies them. The printed former switch shelf can remain empty; no structural redesign is required.

## Battery monitoring and charging

**The XIAO Sense can read the battery without extra hardware.** Its onboard voltage divider presents a reduced battery voltage to ADC pin **P0.31**; drive **P0.14 LOW** to enable that reading. The reviewed schematic uses 1 MΩ/510 kΩ divider resistors, but board revisions and ADC settings can change the conversion, so calibrate the reported volts against a multimeter at the actual BAT pads. Do not assume a raw ADC count is directly the cell voltage. [Seeed's pin/charging documentation](https://wiki.seeedstudio.com/XIAO_BLE/) specifically warns that driving P0.14 HIGH can put P0.31 at its input limit during charging; keep P0.14 LOW while reading and never drive it HIGH while charging. Raw Nordic pin names are not necessarily Arduino D-pin numbers. The PTK servos have ordinary PWM command inputs and **no battery-voltage telemetry**; their three wires cannot report cell state.

Version 0.8 samples the onboard battery divider, requires at least **3.7 V** before arming and stops PWM after two consecutive readings below **3.6 V** (or immediately below **3.4 V**), but Rev B has **no software-controlled battery or servo power disconnect**. Stopping pulses does not eliminate servo idle current or protect a forgotten pack from over-discharge. Monitoring and the motion guard are implemented; divider/ADC calibration against a meter remains pending. USB connection alone does not establish net charging. Unplug the battery when low and remove both battery and USB for storage or wiring work. Voltage under load is not an accurate state-of-charge percentage and can miss brief dips.

**Routine USB-C charging:** leave the battery connected to XIAO BAT+/GND and unplug **both complete servo connectors** before connecting USB. The [BQ25101](https://www.ti.com/product/BQ25101) charges toward 4.2 V on the same BAT+ node used by the direct-powered servos. Firmware cannot isolate that node in Rev B. The [Seeed battery/charging documentation](https://wiki.seeedstudio.com/XIAO_BLE/) and charger architecture explain why disconnecting the battery alone is insufficient with USB attached. No separate charger is added, and the pack does not need to be removed from the robot for charging.

For in-robot charging, [Seeed documents](https://wiki.seeedstudio.com/XIAO_BLE/) configuring **P0.13 as an output driven LOW** for approximately **100 mA**, or as a high-impedance input without pulls for approximately **50 mA**. In the regular Seeed nRF52 core used by the [bench sketch](firmware/README.md), use `digitalWrite(PIN_CHARGING_CURRENT, LOW); pinMode(PIN_CHARGING_CURRENT, OUTPUT);` and keep that state for the charging session. That core maps `PIN_CHARGING_CURRENT` to Arduino pin 22 / Nordic P0.13; Arduino pin 13 is an LED. Other cores use different pin-name mappings. This is a firmware setting, not a physical switch or battery-voltage sense pin. At 100 mA (0.2C), an empty 500 mAh pack needs at least about five hours plus the voltage-taper phase. The 50 mA setting is approximately 0.1C and could hit the [charger's fixed ten-hour safety timer](https://www.ti.com/product/BQ25101) before completing. The charger IC itself is specified for a maximum of **250 mA**, and Seeed exposes only the approximately 50/100 mA settings on this board, so **500 mA cannot be selected by software on the XIAO**. The XIAO's charge LED indicates charging activity; verify final battery voltage rather than treating the LED alone as a complete fuel gauge. **Do not apply battery voltage to 3V3 or 5 V to BAT.** For routine charging the battery can stay connected, but unplug both servo plugs. For full OFF, disconnect battery and USB.

## Power budget and brownout check

Seller data for the [PTK 7465 MG family](https://manuals.plus/ae/1005008789583991) reports about **1 A stall current per servo at 4.8 V**. That is only a provisional sizing comparison for two servos (about 2 A), **not** a measurement or guaranteed limit for the purchased non-W units at 3.6–4.2 V. The selected [500 mAh, 25C battery](https://www.horizonhobby.com/product/1s-3.7v-500mah-25c-li-po-battery-jst-rcy/EFLB5001S25.html) advertises a nominal 0.5 Ah × 25 = **12.5 A discharge rating**, above the comparison load on paper. A C rating does not specify voltage sag at the board, connector loss, cell aging, or how long the servos can sustain a mechanical stall. Measure peak draw and sag with the actual pair.

The XIAO's [schematic](https://files.seeedstudio.com/wiki/XIAO-BLE/Seeed_Studio_XIAO_nRF52840_PDF.pdf) shows a **3.3 V, 250 mA regulator** for its electronics. Two servos must take their current from the battery bus rather than this regulator. When the shared battery sags, the regulator can still lose headroom even though motor current bypasses the controller. The [regulator datasheet](https://www.sg-micro.com/product/SGM2040) gives performance under specified conditions; actual battery/harness behavior requires measurement.

For the first measurement, use a **DC multimeter**, two thin insulated temporary sense wires, and clips. With the battery **unplugged**, solder one sense wire to the XIAO-side BAT+ joint and one to its GND joint; insulate and strain-relieve both so no clip can short the tiny pads or snag a moving link. Put the meter in **DC-volts mode, in parallel** across those wires (red to BAT+, black to GND). Secure the robot's base, run a repeatable two-servo motion, and watch the voltage while the arms move. To check the regulated rail too, add a **third temporary sense wire to XIAO 3V3 while power is disconnected**, then repeat with the meter's red clip on that wire and black still on GND; a second meter lets you observe both at once. Do **not** use the meter's current/A jack across the battery. A meter with MIN/MAX is helpful for slow sag, but many meters miss millisecond dips. A two-channel oscilloscope at the same test wires is the follow-up tool if resets occur or exact transient minima matter. The robot's built-in battery ADC can log voltage during later untethered tests after calibration, but it can miss brief dips too. [Seeed documents the BAT measurement pins and the required P0.14 LOW state](https://wiki.seeedstudio.com/XIAO_BLE/).

Before untethered operation, test around 4.2, 3.8, and 3.6 V cell voltage while commanding both servos through the fastest intended reversals and brief high-load motions; do not hold a servo at stall. As a conservative prototype acceptance target, the **3V3 rail should stay above 3.2 V and the controller should never reset** during those tests. That 3.2 V value is a design target, not the chip's published reset threshold. If it fails, first improve the battery connector, wiring and cell choice or raise the loaded-voltage warning threshold; then consider the optional capacitor for short transients. A capacitor will not fix sustained sag.

**Do not operate this design below 3.0 V at the cell.** The PTK servo's *published* lower operating limit is around **5 V** on the [manufacturer's related 7465 MG-D page](https://www.ptkhobby.com/en/sys-pd/234.html), so **all direct 1S operation is outside that rating**, despite the reference robot's 3.7 V success. The XIAO's 3.3 V regulator cannot maintain a 3.3 V output from a battery below 3.3 V, so a reset or unstable sensing is possible. The selected single-cell LiPo should be shut down well before 3.0 V; [Horizon Hobby's LiPo equipment guidance](https://www.horizonhobby.com/on/demandware.static/-/Sites-horizon-master/default/Manuals/EFLU02050_MANUAL_EN.pdf) uses a 3.0 V-per-cell low-voltage cutoff. Our initial **3.6 V loaded manual-stop threshold** is intentionally earlier to preserve regulator headroom and battery life, pending measurement. Raise that threshold if recovery weakens sooner. Rev B can only stop PWM and warn on low voltage; it has no physical electronic cutoff. Disconnect the pack manually when low and for storage; do not assume the RC battery includes its own low-voltage protection.

Use a watchdog and explicit arming state. Invalid sensor data, a stale control loop and low voltage should stop PWM, drive D0/D1 LOW and indicate a fault; they cannot cut the direct supply. D2 is unused. Disconnect both servo plugs for routine USB charge/program mode. Start with a USB command to arm during bench development, then add a deliberate untethered arming gesture/button behavior. No wireless link is needed during normal operation.

## Why 500 mAh, and estimated runtime

The 500 mAh EFLB5001S25 was a **conservative prototype choice**, not the smallest proven pack. Its stated 25C discharge rating corresponds to 12.5 A on paper, above the PTK-family's approximate 2 A combined 4.8 V stall-current comparison. It has a matching RCY connector and dimensions for the current CAD, but at roughly 14.5 g and 59.5 × 19 × 7.5 mm it is a major driver of base size. The reference robot uses 220 mAh. A smaller, suitably high-discharge cell may be better after measuring actual recovery pulses and voltage sag.

Runtime cannot be predicted from stall current or capacity alone: it depends on how frequently the policy moves the joints, how hard it pushes on the floor, voltage sag, and the chosen 3.6 V loaded manual-stop threshold. The purchased PTK pair has **no verified 1S current profile**. [Seeed lists 10.38 mA](https://files.seeedstudio.com/wiki/XIAO/Seeed-Studio-XIAO-Series-SOM-Datasheet.pdf) for a normally running XIAO Sense. For planning only, assume **300–400 mAh usable** before the early manual voltage stop and divide that by measured *average total battery current*:

| Average current, including both servos and controller | Illustrative runtime to manual stop |
|---:|---:|
| 0.25 A | 1.2–1.6 h |
| 0.5 A | 36–48 min |
| 1.0 A | 18–24 min |

Those are arithmetic scenarios, **not measured endurance claims**. As a first planning range for repeated active recoveries, expect tens of minutes to about an hour, then replace this estimate with battery-side current logging over representative episodes. A stationary upright robot may last much longer. The 500 mAh pack also takes at least about five hours plus taper on the XIAO's 100 mA charger; a smaller cell would improve both size and charging time if it passes the loaded-voltage test.

## Servo selection and limits

The [manufacturer's related PTK 7465 MG-D page](https://www.ptkhobby.com/en/sys-pd/234.html) specifies a 23.9 × 12 × 26.6 mm package, 25T ~5 mm output spline and about 5–8.4 V operating range. Family listings report approximately **3.8 kg·cm stall torque** and **0.11 s/60° no-load speed at 5 V**; those are neither continuous torque nor 1S performance figures. The [reference robot](https://homemadegarbage.com/rl13) used PTK 7465 MG on one cell and the author reports 3.7 V worked without boost. Verify the purchased non-W units and XIAO's 3.3 V control signal on the bench. If the servos weaken unacceptably as the cell discharges, reconsider power architecture based on measurements.

The simulation's **0.045–0.070 N·m torque limit and 3–5 rad/s speed** are conservative design assumptions to replace with measurements. They are not manufacturer continuous-duty ratings. Avoid using the reference model's 1 N·m actuator limit for these micro servos.

PTK-family listings commonly describe **500–2500 µs for about ±90°**, but variant-specific center and endpoint settings differ. Start with the horn removed and a small **1450–1550 µs** sweep at 50 Hz; measure angle and direction, then widen gradually and set software stops for the actual mechanism. Do not assume the full advertised ±90° is safe with the printed links. The proposed robot joint range remains ±80° pending clearance and wire-loop checks. Later test whether a higher pulse refresh rate gives any benefit; a 50 Hz command rate matches the current policy loop.

These servos provide no external joint-angle feedback. Firmware stores commanded targets; it does not know the actual shaft angle under impact or stall. Training must model lag, backlash and load effects, and policy observations must not secretly use simulator joint encoders. The IMU belongs on the base so its orientation measures platform recovery.

## Mechanics and order of work

At a hypothetical 100 g assembled mass, a simple weight moment about a 35 mm base edge is approximately **0.034 N·m**. The centered reinforced design has not been weighed; this is a sizing example, not a mass prediction or proof that the actuator can execute a recovery trajectory. Floor contact, paddle reach, dynamic impulses and orientation can make the required joint torque much larger. The upper joint's job includes pushing on the floor, not merely lifting its own paddle.

1. Print the servo, horn and pivot fit coupons; check the case, flange holes, actual horn, bearing and pin. Measure the delivered battery as well. Correct CAD dimensions before printing the complete set.
2. Center one unloaded servo at its measured neutral. Install the correct OEM horn and output screw; establish angle direction and pulse calibration. Repeat for the second servo.
3. Assemble the two ear mounts and the two lateral horn adapters using the BOM. Keep screw ends and nut flats out of moving envelopes. Trim excess screw projection if required.
4. Slide the battery into the centered tunnel from the +X end. Retain it at the end with a tie through the two side-wall windows; do not compress or abrade the pouch. Secure and insulate the XIAO on its shelf, leave the former switch shelf empty, confirm USB-C access, and document sensor-axis orientation.
5. Wire and polarity-check with the battery disconnected. Test the MCU from USB first with both complete servo plugs disconnected. Then energize one servo on a current-limited bench supply, followed by both. Check voltage sag during direction reversals.
6. Test full intended travel slowly while supported. Then try four cardinal side falls, diagonal falls and inverted starts on a controlled surface. Start with scripted slow motion and a small search over safe waypoint sequences.
7. Weigh each moving assembly, measure COM, current, loaded response and floor friction. Feed those values back into MuJoCo before substantive policy training.

The base does not have arbitrary soft rubber feet: their traction and compliance would change the contact model. Begin on one repeatable hard surface, then randomize/test additional surfaces. The paddle contact edge and base width are the main geometry tuning parameters. If a pose wedges into a stable resting configuration from which neither joint can create a useful contact force, redesign that geometry; RL cannot remove the physical constraint.
