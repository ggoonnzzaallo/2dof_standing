# Rev C — one Pololu battery master switch

Controller **0.6** adds automatic battery-only startup and USB-at-boot charge mode, retaining the reboot-only 60-second base-IMU inactivity stop. Wiring is unchanged; PWM shuts down while charging remains available. See [operating instructions](../docs/OPERATING_INSTRUCTIONS.md#automatic-inactivity-stop).

**Signal update, 7 November 2026:** the user reports lower servo signal on **D8 / 8** and upper on **D7 / 7**. Controller 0.4 matches these pins and was uploaded on 7 November 2026; no-PWM checks and standalone arming passed, with normal joint response confirmed by the user. Full Rev C power/charging commissioning remains pending; the earlier confirmed harness was [Rev B](REV_B_NOTES.md). Rev C reinstalls **one existing Pololu 2810 LV** upstream of both the XIAO and servos. No second switch board, charger, MOSFET, diode, resistor or capacitor is added. D2 stays unused.

Open the [complete schematic PDF](REV_C_WIRING.pdf), [SVG](REV_C_WIRING.svg), [PNG](REV_C_WIRING.png), or [large-text phone map](REV_C_PHONE_WIRING.png). These are connection maps; use the physical board's printed pad labels, not drawing positions.

**Starting with loose components? Follow the [complete from-scratch assembly guide](FROM_SCRATCH.md): two buses and twelve numbered wire branches, including PWM.**

![Rev C complete wiring](REV_C_WIRING.png)

## Every connection

| Physical net / wire | Join these points | Purpose |
|---|---|---|
| Raw battery positive | Battery RCY pigtail **+ → Pololu VIN only** | The battery is isolated from every load when the switch is OFF and USB is absent. |
| **J1 SWITCHED+, 4-way bus** | Pololu **VOUT**, XIAO underside **BAT+**, lower servo red, upper servo red | Powers the controller and both servos through one switch. Each servo draws through the bus, not through XIAO traces or the BAT pad. |
| **J2 common GND, 5-way bus** | Battery negative, Pololu **GND**, one XIAO **GND or BAT−**, both servo grounds | Common return. Negative is not switched. |
| XIAO **D8 / marked 8** | Lower servo signal | Lower PWM. |
| XIAO **D7 / marked 7** | Upper servo signal | Upper PWM. |
| Former XIAO **D0 / 0** and **D1 / 1** | **No wires** | Superseded by D8/D7 on 7 November 2026. |
| XIAO **D2 / marked 2** | **No wire** | No software switch override. |
| Pololu **ON** and **SW** control pads | **No wires** | Operate only the board's physical slider. Do not connect D2 to ON. |
| XIAO USB-C | Existing USB cable | Programming and onboard charging. No wire from 5V/VBUS or 3V3 to either servo. |

Each existing servo plug still carries positive, ground and signal. The battery RCY and servo plugs remain **inside** the cup for service, with no routine need to reach them through a window. The [cup layout](../cad/electronics_pod/README.md) exposes only the USB port and one slider. The Pololu is supported on low insulated PSA lands and locating stops in the corner; never use its electrical pads as mounting holes.

## Switch and software states

| Switch | USB | Software | Result |
|---|---|---|---|
| ON | Absent | Explicitly armed | Battery powers XIAO and servos; standalone recovery continues. |
| ON | Connected | **`./robot charge`** | PWM detached and D8/D7 LOW. The onboard charger is connected to the battery through the Pololu. Servos still receive power and can consume idle current. |
| OFF | Absent | Any | Battery isolated from XIAO and servos; only switch leakage and cell self-discharge remain. |
| OFF | Connected | Any | Battery isolated, so **it cannot charge**. USB can still power the XIAO and shared servo rail through the charger. This is not full OFF. |

**Storage OFF = unplug USB + slide OFF. Charging = slide ON + USB-at-boot charge mode (or explicit `./robot charge`).** Software mode 5 indicates PWM inhibition, not measured positive battery current, a physical servo cutoff or a fuel-gauge result. The charger operates automatically when USB is present; the command stops motion rather than enabling the charger IC.

## Commissioning the new harness

1. Unplug **battery and USB**. Open the cup/base and unplug the servo plugs while soldering and doing the first USB-only firmware upload.
2. Follow the [twelve-branch wiring table](FROM_SCRATCH.md#connect-these-twelve-wire-branches). Battery positive goes to **VIN only**, and **VOUT** feeds J1. J1 branches to BAT+ and both servo positives. Do not bypass the Pololu with another battery-positive connection.
3. J2 joins battery negative, Pololu GND, XIAO GND and both servo grounds. Connect D8/D7 to the lower/upper signal wires; leave D2/ON/SW unconnected. Insulate joints separately and leave solder/lead bends clear beneath the PCB.
4. With all power absent, check polarity, common-ground continuity and absence of a low-resistance positive-to-ground short. A MOSFET switch is not an ordinary mechanical contact; resistance across VIN/VOUT by itself is not a definitive on/off test.
5. Build/upload controller **0.6** as described in the [firmware guide](../firmware/policy_control/README.md). It is now uploaded; see the [deployment record](../firmware/policy_control/results/2026-11-07/deployment_0_6.json). Through-switch charging/current checks remain pending.
6. Battery-only OFF with USB absent should shut the robot down. ON with USB absent now **automatically starts recovery after initialization and neutral acquisition**. For a no-PWM check instead, boot with USB present; that selects CHARGE (5). Keep the switch ON to connect the battery for charging. `./robot charge` remains available as an explicit command.
7. Verify charging current actually reaches the cell through the enabled Pololu, and measure the pair's no-PWM idle load and charge completion/termination. A series current measurement at the battery connection is useful; do not put a meter's current input directly across the cell. USB current or voltage alone does not establish net battery charging.
8. Confirm OFF with USB removed eliminates the ongoing controller/servo drain. Test slider travel and USB insertion before closing the original base over the cup.

Charging through the enabled switch is an engineering inference from the slide board's back-to-back MOSFET schematic, not an observed result on this unit. Pololu separately confirms reverse charging for its related pushbutton switch; that is corroboration, **not an exact-model bench test**. Keep commissioning results separate from the existing recovery evidence.

## Charging limits

The existing XIAO charging configuration remains approximately **100 mA**, selected by `PIN_CHARGING_CURRENT` LOW. Servo idle current and the switch LED consume some of that output; movement can exceed it and discharge the cell while USB is connected. The charger has a shared battery/load output, not a separate managed servo supply.

TI permits a parallel system load provided charging completes within the fixed ten-hour safety timer. Nonzero idle current can also affect termination/indicator behavior. The no-PWM load and complete charging cycle **must be characterized** before treating this as a validated connector-free charging setup. If idle load prevents completion, this one-switch/no-extra-electronics constraint cannot fix that by software alone; revisit the design rather than claim charging is verified.

With switch OFF, the XIAO ADC reads the isolated BAT/charger node rather than the cell. With switch ON it is an approximate cell-voltage reading affected by charging and switch/wire loss. There is no switch-position sensor, current sensor, physical low-voltage cutoff or automatic physical OFF in this revision.

## Reproduction and sources

```sh
.tools/arduino/python/bin/python electrical/render_rev_c.py
```

[Pololu 2810 operation and schematic](https://www.pololu.com/product/2810), [related pushbutton reverse-charging discussion](https://forum.pololu.com/t/charge-lipo-through-mini-pushbutton-power-switch-lv/20861), [XIAO schematic](https://files.seeedstudio.com/wiki/XIAO-BLE/Seeed_Studio_XIAO_nRF52840_PDF.pdf), [Seeed charging settings](https://wiki.seeedstudio.com/XIAO_BLE/#battery-charging-current), and [TI BQ25101 parallel-load/timer limitations](https://www.ti.com/product/BQ25101).

[Rev A](REV_A_WIRING.pdf) and [Rev B](REV_B_NOTES.md) remain historical. Rev A switches only the servos; **do not use its connections for this master-switch revision**.
