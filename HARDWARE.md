# Hardware and commissioning

The IMU is the LSM6DS3TR-C chip **on the XIAO nRF52840 Sense PCB**. Mount that PCB rigidly on the base, near the controller envelope shown in `cad/assembly.step`. There is no separate IMU module or IMU wire harness. The reference ATOM Matrix also contains its own IMU (MPU6886). See the [board comparison and parts-count options](docs/CONTROLLER_DECISION.md).

## Power and signals

```text
EFLB5001S25 1S battery / keyed RCY connector
  + ----+---------------------------- XIAO BAT+
        +---- Pololu 2810 VIN
                   VOUT ----+-------- Servo 1 positive
                            +-------- Servo 2 positive
  - ----+---------------------------- XIAO BAT- / GND
        +---------------------------- Pololu GND
        +---------------------------- Both servo grounds

XIAO D0 ---------------- Servo 1 signal
XIAO D1 ---------------- Servo 2 signal
XIAO D2 ---------------- Pololu ON
USB-C ------------------ XIAO programming + onboard charging
```

**The servos are not powered by the XIAO.** At the RCY pigtail, split battery positive into a thin XIAO BAT+ branch and a separate, short power branch through the Pololu switch to both servo red leads. Split battery negative into XIAO BAT−/GND and both servo black/brown leads at the same battery-side junction. Only the two servo signal leads and the switch's ON control lead connect to XIAO GPIOs. The shared ground gives those signals a common reference; the motor current returns directly to the battery junction, not through the controller board. Never connect servo red leads to XIAO 3V3 or 5V/VBUS, and do not route motor current through tiny PCB traces or a solderless breadboard.

Keep the high-current wiring short and secure. No external capacitor or signal resistors are needed in this first wiring layout. Measure the battery voltage at the controller during hard servo direction changes; add the optional capacitor from `BOM.md` across the switched servo supply only if transients or resets appear. A capacitor cannot rescue an undersized battery or long resistive power wiring. [Pololu notes that capacitors near its switch can reduce spikes when interrupting large currents](https://www.pololu.com/product/2810).

Leave the **Pololu's physical slide OFF**. In that position D2 high enables the servo supply; low or disconnected disables it. Sliding it ON overrides software power-off. Initialize D2 low before any PWM setup. Before cutting servo power, stop both PWM outputs and set their pins low; keep them low until servo power is restored. This avoids intentionally driving an unpowered servo through its signal pin. Check the actual servos for back-powering; two optional 1 kΩ series resistors can limit that current if it occurs, but do not replace correct sequencing. [Pololu 2810 documentation](https://www.pololu.com/product/2810).

Use the XIAO BAT pads for the standard 1S battery. **Do not apply battery voltage to 3V3, and do not connect 5 V to BAT.** The board has its own charging/regulation circuit. During USB charging/programming, keep servo power disabled: the XIAO's 50–100 mA charging circuit is not a motor supply. Configure 100 mA charging if appropriate to the board revision; approximately 5–7 hours from empty is a planning estimate for 500 mAh, including taper. At the default 50 mA it takes roughly twice as long. Do not assume power-path or charger behavior from a different XIAO board. [Seeed board documentation and schematic links](https://wiki.seeedstudio.com/XIAO_BLE/).

The battery remains connected to the MCU when servos are disabled. Firmware must enter low-power sleep after a low-battery trip; **unplug the RCY for storage and a true power-off**. Start with a conservative loaded-voltage stop near **3.6 V at the XIAO BAT pads**, latched until recharge/restart; refine only after measuring cell sag and the MCU rail under load. This is an initial engineering setting, not a proven cell-protection or no-reset threshold. Measure using the board's battery-divider circuit and the correct board variant's pins/reference. On the reviewed schematic, the divider uses P0.31 ADC with its low end switched by P0.14; use the exact revision's resistor ratio and calibrate against a meter. [Seeed warns that driving P0.14 high during charging can put P0.31 at its input limit](https://wiki.seeedstudio.com/battery_charging_considerations/). Raw Nordic pin names are not Arduino D-pin numbers. This is a firmware requirement, not a completed firmware implementation.

## Power budget and brownout check

The [FT90M manufacturer specification](https://www.feetechrc.com/Data/feetechrc/upload/file/20210809/6376411509095078411776244.pdf) gives **0.8 A stall current per servo at 4.8 V** and **1.0 A at 6 V**. For two simultaneously loaded servos, **1.6 A at 4.8 V** is a useful sizing comparison; the actual peak at 3.5–4.2 V is **not specified** and must be measured. The selected [500 mAh, 25C battery](https://www.horizonhobby.com/product/1s-3.7v-500mah-25c-li-po-battery-jst-rcy/EFLB5001S25.html) advertises a nominal 0.5 Ah × 25 = **12.5 A discharge rating**, so its published current rating is above that comparison load. A C rating does not specify voltage sag at the board, connector loss, cell aging, or how long the servos can sustain a mechanical stall.

The [Pololu 2810 LV switch](https://www.pololu.com/product/2810) is rated for single-cell voltages and lists 3 A continuous at its 55 °C reference point. The XIAO's [schematic](https://files.seeedstudio.com/wiki/XIAO-BLE/Seeed_Studio_XIAO_nRF52840_PDF.pdf) instead shows a **3.3 V, 250 mA regulator** for its electronics. This is why the servo-power split must occur **before** the XIAO: two servos would exceed that regulator by a wide margin. The regulator also needs input headroom; when the shared battery sags near the end of a run, the 3.3 V rail can dip even though the motors do not draw through the board. The [regulator datasheet](https://www.sg-micro.com/product/SGM2040) gives low dropout under specified conditions, but it does not guarantee behavior for this unmeasured battery/harness and simultaneous servo load.

For the first measurement, use a **DC multimeter**, two thin insulated temporary sense wires, and clips. With the battery **unplugged**, solder one sense wire to the XIAO-side BAT+ joint and one to its GND joint; insulate and strain-relieve both so no clip can short the tiny pads or snag a moving link. Put the meter in **DC-volts mode, in parallel** across those wires (red to BAT+, black to GND). Secure the robot's base, run a repeatable two-servo motion, and watch the voltage while the arms move. To check the regulated rail too, add a **third temporary sense wire to XIAO 3V3 while power is disconnected**, then repeat with the meter's red clip on that wire and black still on GND; a second meter lets you observe both at once. Do **not** use the meter's current/A jack across the battery. A meter with MIN/MAX is helpful for slow sag, but many meters miss millisecond dips. A two-channel oscilloscope at the same test wires is the follow-up tool if resets occur or exact transient minima matter. The robot's built-in battery ADC can log voltage during later untethered tests after calibration, but it can miss brief dips too. [Seeed documents the BAT measurement pins and the required P0.14 LOW state](https://wiki.seeedstudio.com/XIAO_BLE/).

Before untethered operation, test around 4.2, 3.8, and 3.6 V cell voltage while commanding both servos through the fastest intended reversals and brief high-load motions; do not hold a servo at stall. As a conservative prototype acceptance target, the **3V3 rail should stay above 3.2 V and the controller should never reset** during those tests. That 3.2 V value is a design target, not the chip's published reset threshold. If it fails, first improve the battery connector, wiring and cell choice or raise the loaded-voltage cutoff; then consider the optional capacitor for short transients. A capacitor will not fix sustained sag.

**Do not operate this design below 3.0 V at the cell.** The servo's published lower operating limit is **3.0 V**; below it, torque and control are unspecified. The XIAO's 3.3 V regulator cannot maintain a 3.3 V output from a battery below 3.3 V, so a reset or unstable sensing is possible. The selected single-cell LiPo should be shut down well before this point; [Horizon Hobby's LiPo equipment guidance](https://www.horizonhobby.com/on/demandware.static/-/Sites-horizon-master/default/Manuals/EFLU02050_MANUAL_EN.pdf) uses a 3.0 V-per-cell low-voltage cutoff. Our initial **3.6 V loaded servo cutoff** is intentionally earlier to preserve regulator headroom and battery life, pending measurement. The cutoff firmware is still a required implementation, and the battery should be disconnected for storage; do not assume the selected RC battery includes its own low-voltage protection.

Use a watchdog and explicit arming state. Charge/program mode, invalid sensor data, stale control loop and low voltage should leave D2 low. Start with a USB command to arm during bench development, then add a deliberate untethered arming gesture/button behavior. No wireless link is needed during normal operation.

## Servo selection and limits

The [FT90M manufacturer sheet](https://evelta.com/content/datasheets/501-FT90M.pdf) rates input at 3–8.4 V and signal high at 2–5 V, so a 3.3 V MCU signal is suitable without level shifting. Published performance at 4.8 V: 1.89 kg·cm stall torque, 0.8 A stall current and 0.125 s/60 degrees no-load speed. The 1S operating range is supported, but exact torque/speed at 3.5–4.2 V are not tabulated.

The simulation's **0.045–0.070 N·m torque limit and 3–5 rad/s speed** are conservative design assumptions to replace with measurements. They are not manufacturer continuous-duty ratings. Avoid using the reference model's 1 N·m actuator limit for these micro servos.

This FT90M sheet specifies an unusually wide **280-degree travel over 1000–2000 microseconds**, with 1500 microseconds neutral at 50 Hz. Seller-specific programming may differ. Start with the horn removed and a small **1450–1550 microsecond** command sweep, measure angle, then establish a safe mapping and physical soft stops. Do not blindly use a generic 500–2500 microsecond library sweep. Proposed robot joint range is ±80 degrees, subject to the real wire and horn clearances. The FT90M-FB is a different variant; do not silently substitute its pulse mapping.

These servos provide no external joint-angle feedback. Firmware stores commanded targets; it does not know the actual shaft angle under impact or stall. Training must model lag, backlash and load effects, and policy observations must not secretly use simulator joint encoders. The IMU belongs on the base so its orientation measures platform recovery.

## Mechanics and order of work

At 80 g, a simple weight moment about a 35 mm base edge is approximately **0.027 N·m**. That is a useful sizing scale, not a proof that the actuator can execute a recovery trajectory. Floor contact, paddle reach, dynamic impulses and orientation can make the required joint torque much larger. The upper joint's job includes pushing on the floor, not merely lifting its own light paddle.

1. Print a fit sample (base mount or sliced mount section), check the case, flange holes and actual horn. Correct HORN_FACE and hole locations before printing the complete set.
2. Center one unloaded servo at its measured neutral. Install the correct OEM horn and output screw; establish angle direction and pulse calibration. Repeat for the second servo.
3. Assemble the two ear mounts and the two lateral horn adapters using the BOM. Keep screw ends and nut flats out of moving envelopes. Trim excess screw projection if required.
4. Fit battery below its guard with the guard feet resting on the base. Strap across the guard. Nothing sharp or a tie edge should bear directly on the pouch. Secure the controller rigidly, insulate its underside and document sensor-axis orientation.
5. Wire and polarity-check with the battery disconnected. Test the MCU from USB first with the servo supply disabled. Then energize one servo on a current-limited bench supply, followed by both. Check voltage sag during direction reversals.
6. Test full intended travel slowly while supported. Then try four cardinal side falls, diagonal falls and inverted starts on a controlled surface. Start with scripted slow motion and a small search over safe waypoint sequences.
7. Weigh each moving assembly, measure COM, current, loaded response and floor friction. Feed those values back into MuJoCo before substantive policy training.

The base does not have arbitrary soft rubber feet: their traction and compliance would change the contact model. Begin on one repeatable hard surface, then randomize/test additional surfaces. The paddle contact edge and base width are the main geometry tuning parameters. If a pose wedges into a stable resting configuration from which neither joint can create a useful contact force, redesign that geometry; RL cannot remove the physical constraint.
