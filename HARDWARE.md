# Hardware and commissioning

The IMU is the LSM6DS3TR-C chip **on the XIAO nRF52840 Sense PCB**. Mount that PCB rigidly on the base, near the controller envelope shown in `cad/assembly.step`. There is no separate IMU module or IMU wire harness. The reference ATOM Matrix also contains its own IMU (MPU6886). See the [board comparison and parts-count options](docs/CONTROLLER_DECISION.md).

## Power and signals

```text
EFLB5001S25 1S battery / keyed RCY connector
  + ----+---------------------------- XIAO BAT+
        +---- Pololu 2810 VIN
                   VOUT ----+-------- Servo 1 positive
                            +-------- Servo 2 positive
                            +-------- 1000 uF capacitor (+)
  - ----+---------------------------- XIAO BAT- / GND
        +---------------------------- Pololu GND
        +---------------------------- Both servo grounds
        +---------------------------- Capacitor (-)

XIAO D0 ---- 1 kohm ---- Servo 1 signal
XIAO D1 ---- 1 kohm ---- Servo 2 signal
XIAO D2 ---------------- Pololu ON
USB-C ------------------ XIAO programming + onboard charging
```

Make the power split at the battery harness. Servo current must not flow through XIAO 3V3, 5V/VBUS, tiny PCB traces or a solderless breadboard. Route controller ground back to the same power-star point as servo ground. Observe capacitor polarity. Secure and insulate the capacitor next to the switch; it is not included in the CAD envelope. The capacitor suppresses brief disturbances; it cannot rescue an undersized battery or long resistive power wiring.

Leave the **Pololu's physical slide OFF**. In that position D2 high enables the servo supply; low or disconnected disables it. Sliding it ON overrides software power-off. Initialize D2 low before any PWM setup, and hold PWM outputs low before cutting servo power to avoid feeding an unpowered servo through its signal pin. The series resistors limit accidental injection current but do not replace that sequencing. [Pololu 2810 documentation](https://www.pololu.com/product/2810).

Use the XIAO BAT pads for the standard 1S battery. **Do not apply battery voltage to 3V3, and do not connect 5 V to BAT.** The board has its own charging/regulation circuit. During USB charging/programming, keep servo power disabled. Configure 100 mA charging if appropriate to the board revision; approximately 5–7 hours from empty is a planning estimate for 500 mAh, including taper. At the default 50 mA it takes roughly twice as long. Do not assume power-path or charger behavior from a different XIAO board. [Seeed board documentation and schematic links](https://wiki.seeedstudio.com/XIAO_BLE/).

The battery remains connected to the MCU when servos are disabled. Firmware must enter low-power sleep after a low-battery trip; **unplug the RCY for storage and a true power-off**. Use a loaded-voltage stop near **3.5 V**, initially latched until recharge/restart; refine only after checking cell sag and MCU rail headroom. Measure using the board's battery-divider circuit and the correct board variant's pins/reference. On the reviewed schematic, the divider uses P0.31 ADC with its low end switched by P0.14; use the exact revision's resistor ratio and calibrate against a meter. Raw Nordic pin names are not Arduino D-pin numbers. This is a firmware requirement, not a completed firmware implementation.

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
