# First power-up, servo centering and small-motion checks

Use `servo_center/servo_center.ino` for the wired XIAO **nRF52840 Sense**, two PTK 7465 MG servos, and Pololu **2810 LV**. It starts with D2 LOW and both servo signals LOW. It does not move on boot. Serial commands test the switch, center a servo or jog one unloaded servo at a time; each command has a short timeout and closing the serial monitor disables the rail. This is supervised bench firmware; it has no automatic battery cutoff or policy inference.

## 1. Unpowered checks

Keep the servo horns and driven printed parts off the splines. Leave the Pololu slide physically **OFF**. With battery and USB unplugged, inspect polarity, solder bridges and insulation. A meter should show no sustained near-zero resistance between battery + and GND or between servo + and GND; a momentary continuity beep while capacitors charge is not necessarily a short. Confirm battery + reaches **Pololu VIN and XIAO BAT+**, and that the 3V3 pin has no motor wiring. The Pololu VIN solder point can be the shared positive junction, with one battery lead and a short branch to XIAO BAT+.

## 2. Build and upload from VS Code

Open the `2dof_standing` repository folder in VS Code. No Arduino IDE or editor extension is required. The project uses Arduino's command-line compiler with Seeed's regular nRF52 core; the commands below are also available under **Terminal → Run Task → Robot: …**.

For a fresh checkout, install the project-local tools once:

```sh
python3 scripts/robot.py setup
```

This macOS setup stores tools under `.tools/`, uses the pinned **Seeed nRF52 Boards 1.1.13** package and bundled Servo/TinyUSB libraries, and installs an isolated Python uploader. On Apple Silicon it uses **Arm GNU 13.2.Rel1** instead of Seeed's bundled Intel-only compiler. Generated firmware goes into `build/`. Neither folder is committed to git. Python 3.12 or newer, macOS Command Line Tools (`cc`/`make`) and a network connection are needed for initial setup; installed tools build offline afterward. The source follows [Seeed's board setup and pin documentation](https://wiki.seeedstudio.com/XIAO_BLE/).

With the battery **unplugged**, horns off, Pololu slide OFF, and a USB data cable connected:

```sh
python3 scripts/robot.py build
python3 scripts/robot.py ports
python3 scripts/robot.py upload
python3 scripts/robot.py check
```

Upload auto-selects a port only if exactly one board is identified as **Seeed XIAO nRF52840 Sense**. If needed, use `--port /dev/cu.usbmodem…`. The `check` command opens USB serial and sends **`help` followed by `off`**, both of which disarm the motors. It checks the explicit version banner and the `OFF.` acknowledgement. Expect the menu and `OFF.`. If no XIAO port appears, try another data cable. If the bootloader cannot be reached, double-press the small reset button, list ports again and retry the upload.

To operate the bench program interactively:

```sh
python3 scripts/robot.py monitor
```

The monitor uses **115200 baud**, sends a command when you press **Enter**, and exits with **Ctrl+]**. Close any other serial monitor before opening it. The sketch disables servo power when the monitor closes. `Robot: serial monitor` is the corresponding VS Code task.

## 3. Verify the switch before centering

Keep the horns off and the slide OFF. If your servo connectors are removable, leave them unplugged during this switch check; if they are hardwired, keep the shafts free and do not rest a loose printed link on them. Check the pack separately with a meter before connecting it: use a charged 1S cell, and stop this bench test if loaded battery voltage falls below the project's provisional 3.6 V threshold. Connect the pack while leaving USB connected for serial commands.

Use the meter in **DC volts**, with black on common GND and red on the named positive point. Use the voltage jack, never the current jack, for these measurements.

| Check | Expected result |
|---|---|
| Pololu VIN to GND | Approximately the measured battery voltage, no more than 4.2 V for this 1S pack |
| XIAO 3V3 to GND | About 3.3 V |
| Pololu ON to GND after `off` | Near 0 V; this is the control pad connected to D2 |
| Pololu VOUT to GND after `off` | Output is disconnected/floating; a residual meter reading is possible |
| Send `power` | VOUT approximately follows VIN for **3 seconds**, then switches off |
| Send `off`, or `!` | Stops PWM and disables VOUT |

Pololu confirms that the [OFF output is disconnected and floating](https://forum.pololu.com/t/reverse-voltage-on-mini-mosfet-slide-switch-with-2810/11758); it is not actively clamped to GND. A nonzero VOUT reading alone does not prove that the rail can supply current. Record its OFF baseline, verify D2 and Pololu **ON** are near 0 V, then compare the timed enabled and disabled readings. If the output continues to drive a load with `off` and the slide OFF, check D2 → **ON**, the slide position, and whether VIN and VOUT were accidentally bridged. Neither a HIGH/LOW command nor the slide can fix a physical bypass. The slide's **ON** position forces the rail on and defeats software shutdown; see [Pololu's documentation](https://www.pololu.com/product/2810).

For an ambiguous OFF reading, an optional temporary **1–10 kilohm resistor** across VOUT–GND provides a small known test load. Attach/remove it with both power sources unplugged and compare powered OFF/ON voltages. This is a diagnostic aid, not a required permanent BOM component; do not short VOUT to GND or use the meter's current range across the supply. A resistor test has not yet been performed on this build.

## 4. Center, then attach the horns

1. Connect only the **lower** servo if its connector is removable. Keep both splines unloaded. Send `lower`: D0 supplies a nominal **1500 µs** center at approximately **50 Hz**, for **15 seconds**. The rail then turns off. Do not use a sweep example.
2. If the motor settles quietly, send `off`, unplug the battery and USB, and gently fit its supplied OEM horn to the nearest spline tooth that gives the intended upright link pose. Avoid turning the shaft while seating the horn. Use the supplied center screw; do not substitute an unverified thread. Small angular offsets can be calibrated later.
3. Reconnect and command `lower` again. Confirm the horn returns to the same position without binding. Remove power again before fastening the driven print and rear support.
4. Repeat with `upper` for D1. Its `lower`/`upper` names refer to the wiring, not the horn orientation. If both servos are permanently wired, they share switched power, but only the selected servo receives pulses; both must remain unloaded until each is checked.
5. After both centers are established, assemble the moving prints, check passive supports and wire slack, and record alignment offsets. Safe endpoint measurement and slow motion tests come next.

For a clearly visible unloaded motion check, version **0.2** adds `lower-jog` and `upper-jog`. Keep **both horns and driven printed parts off the splines**. The selected output follows **1500 → 1200 → 1800 → 1200 → 1800 → 1200 → 1500 µs**, holding each target for approximately 1.5 seconds before stopping PWM and commanding power off at 10.5 seconds. Actual travel angles are uncalibrated; this is not an endpoint test. Only one servo receives PWM. Ordinary `lower` and `upper` still hold neutral without jogging. Use `off` or `!` to stop early; USB disconnect also stops the test. Do not run the jog with assembled links until clearance and limits have been established.

## 5. Small movements with horns installed

Version **0.3** adds `lower-small` and `upper-small` for a supported assembly with clearance around neutral. Each command follows **1500 → 1450 → 1500 → 1550 → 1500 µs**, approximately 1.5 seconds per target, then stops PWM and commands power off at **7.5 seconds**. These pulse widths are nominal; physical angles are not calibrated. Start at the known assembly-neutral pose. Support the links because the unselected servo receives no PWM and both share the switched rail. Test one joint at a time and inspect for rubbing or cable tension before testing the other. The wider `*-jog` commands remain unloaded/horns-off tests; use the explicit `*-small` commands for this assembled check. Shutdown releases active holding, so keep the arm supported afterward too.

The 1500 µs command is a **nominal starting point**, not a measurement of actual shaft angle. The bundled nRF52 Servo library uses 8 µs timer steps, so a 1500 µs request is represented as approximately 1496 µs; keep this quantization in mind when measuring offsets. Actual pulse timing remains unmeasured. The servos do not report their positions. Direct 1S operation is the reference-project experiment; the related manufacturer's published range starts at 5 V, so don't treat successful centering as proof of adequate loaded performance. If a servo twitches, buzzes persistently, gets hot, or cannot settle unloaded, send `off` and check supply sag, signal/ground wiring and mechanical rubbing before attaching a long arm.

## Bench commands and charging

| Command (newline required) | Action |
|---|---|
| `power` | Servo rail on for 3 seconds, both PWM pins LOW |
| `lower` | D0 at 1500 µs for 15 seconds |
| `upper` | D1 at 1500 µs for 15 seconds |
| `lower-jog` | Unloaded D0 motion between 1200–1800 µs, return to 1500 µs, off at 10.5 seconds |
| `upper-jog` | Same unloaded motion check on D1 |
| `lower-small` | Supported D0 assembly check at 1450–1550 µs around neutral, return to 1500 µs, off at 7.5 seconds |
| `upper-small` | Same small assembly check on D1 |
| `off` | Stop PWM, pull D0/D1 LOW, then D2 LOW |
| `help` | Stop and print commands |
| `!` (no newline needed) | Immediate stop; send a newline before another command |

Commands that enable the rail intentionally work over USB for **supervised bench tests**. This is an explicit exception to the future robot firmware's USB charge interlock. Motors still take current from the connected pack through Pololu, not through the XIAO regulator. Do not attempt a servo test with USB alone and the battery absent: the charger is not a motor supply. For charging, send `off`, close the serial monitor and verify VOUT is off. The sketch selects Seeed's approximately **100 mA** charge setting using the core's `PIN_CHARGING_CURRENT` mapping and keeps `VBAT_ENABLE` LOW. Unplug the battery for storage and true power-off. This is not the complete automatic charge/low-voltage protection firmware.

## Validation

Compilation and supervised hardware commissioning are different checks. See `VALIDATION.md` for command acknowledgements and the user's physical observations. Unloaded movement was confirmed on both servos; actual PWM timing, shaft angles and loaded supply behavior have not been measured by the agent.
