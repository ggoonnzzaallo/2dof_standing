# Purchase BOM — USA delivery, checked 27 September 2026

Prices are full purchase quantities, including unused spares. Availability can change. No orders were placed. Primary sources are linked directly in each row.

**Source preference:** AliExpress is acceptable and may simplify checkout. The links and prices below are the USA supplier baseline that was actually verified. See the [AliExpress search terms and exact acceptance checks](docs/ALIEXPRESS_SOURCING.md); no AliExpress listing or delivered price has been verified yet. The [controller comparison](docs/CONTROLLER_DECISION.md) explains why the XIAO Sense was chosen and which small electrical parts could be omitted in a more minimal prototype.

| Buy quantity | Exact item / purchase link | What it does | Used on robot | Extended price | Verification / selection |
|---:|---|---|---:|---:|---|
| 1 | [Seeed XIAO nRF52840 Sense, 102010469 — DigiKey](https://www.digikey.com/en/products/detail/seeed-technology-co-ltd/102010469/16652896) | The robot’s brain: runs the trained model and commands both servos. Its **LSM6DS3TR-C IMU is soldered onto this same board**, which mounts on the base. The board also charges the battery over USB. Training happens on your computer. | 1 | $15.90 | DigiKey 1597-102010469-ND; stock listed. Buy **Sense**, not the non-Sense or ESP32S3 Sense. |
| 2 | [FEETECH FT90M, Nevermore Stealthmax V2 Servo — Beaverton Milestone Hobby](https://beavertonmilestonehobby.com/products/nevermore-stealthmax-v2-servo) | Move the two arm joints. Each servo combines a motor, gears and an internal position controller, so the XIAO can request an angle instead of directly controlling motor current. | 2 | $17.98 | $8.99 each, variant 44038808305752, live available flag and Add to cart. 32 cm three-wire lead. Seller's second package photo shows matching plastic horns. |
| 1 | [E-flite EFLB5001S25, 500 mAh 1S 25C — Vortex Hobbies](https://vortexhobbies.com/flite-500mah-37v-25c-lipo-battery-eflb5001s25-p-70086.html) | Stores the energy to run the controller and both servos without a cable. This single-cell battery powers them directly, avoiding a separate voltage-boost converter. | 1 | $11.99 | Listed in stock for shipping. 59.5 × 19 × 7.5 mm, 14.5 g. Standard 4.2 V full-charge LiPo with JST-RCY; seller excludes Alaska/Hawaii shipment. |
| 1 | [Pololu 2810 Mini MOSFET Slide Switch, **LV**](https://www.pololu.com/product/2810) | Lets the XIAO turn power to both servos on or off—for example, to stop motion when the battery is low. It switches motor power without making the small controller board carry the motors’ current. | 1 | $4.49 | Servo rail only. [Supply status](https://www.pololu.com/product/2810/supply-outlook) lists available units. Physical switch stays OFF when GPIO controls ON. |
| 1 | [Pololu 2181 male JST-RCY plug, 10 cm 20-AWG leads](https://www.pololu.com/product/2181) | Provides a removable connection between the battery and the robot’s wiring. Unplug it for storage or to disconnect all battery power. | 1 | $2.95 | Mates to battery; verify polarity before soldering. Live [supply status](https://www.pololu.com/product/2181/supply-outlook) showed 386 units. |
| 1 | [Rubycon 6.3YXJ1000M8X11.5, 1000 µF 6.3 V — DigiKey](https://www.digikey.com/en/products/detail/rubycon/6-3YXJ1000M8X11-5/3563358) | Acts as a small, fast energy buffer beside the servos, helping reduce brief voltage dips and electrical noise when the motors change direction. It does not replace the battery or proper power wiring. | 1 | $0.51 | Bulk capacitor across switched servo supply. 8 mm diameter, allow 13 mm height. Stock listed. |
| 2 | [Yageo CFR-25JB-52-1K, 1 kΩ axial — DigiKey](https://www.digikey.com/en/products/detail/yageo/CFR-25JB-52-1K/96) | Limit accidental current through each servo’s control-signal wire, helping protect the electronics when servo power is off. These go in the signal wires, not the motor power wires. | 2 | $0.20 | DigiKey 1.0KQBK-ND; one series resistor in each PWM signal. |
| 10 | [Panduit PLT1M-C, 2.5 mm × ~99 mm cable ties — DigiKey](https://www.digikey.com/en/products/detail/panduit-corp/PLT1M-C/280033) | Hold the battery guard and electronics in place and secure wires so movement does not pull on solder joints. | 6 + 4 spare | $2.29 | 2 battery guard, 1 controller, 1 switch, 2 strain relief. Sold individually; quantity 10 pricing used. |
| 1 pack | [M2×8 Phillips pan-head screws + nuts + flat/lock washers, 25 sets — Harfington](https://www.harfington.com/products/p-1076908) | Secure the servo bodies to the printed mounts and connect the moving arm pieces to the servo horns—the small arms attached to the motor shafts. Nuts retain the screws; flat washers spread pressure on the plastic. | 8 screw/nut/flat-washer sets | $7.23 | SKU a17040600ux0058; US/USD page listed in stock, dispatch in 24 h. US shipping offered; domestic warehouse origin was not established. |
| | **Core purchase subtotal** | | | **$63.54** | **$36.46 remains for shipping/tax/consumables within $100.** |

**Fewest-parts experiment:** omitting the Pololu switch, capacitor and two signal resistors leaves the XIAO Sense, two servos, battery, mating lead, ties and fasteners: **$58.34** at the listed USA prices. This is a bench experiment, not the recommended autonomous wiring: servos remain connected whenever the pack is plugged in, firmware cannot disconnect their power on a low-battery fault, and USB charging with that connected servo rail must be characterized before use. The [controller decision](docs/CONTROLLER_DECISION.md) explains the tradeoff. Rev A's $63.54 BOM retains those parts so that the MCU can shut the servos off.

If needed: [Adafruit 1649 heat-shrink assortment](https://www.adafruit.com/product/1649), **$4.95**, makes the listed purchase subtotal **$68.49**. Heat shrink is insulating tubing that tightens around soldered joints when heated, preventing exposed wires from touching and shorting. Use approximately 15 short sleeves, typically 2–3 mm unshrunk for individual joints and larger sizes for the power splice. Existing heat shrink saves a separate vendor order.

## Exact mechanical allocation

| Location | Fasteners / material |
|---|---|
| Servo 1 ears to integral base mount | 2 × M2×8, 2 × M2 nuts, 2 × M2 flat washers |
| Servo 2 ears to middle-link mount | 2 × M2×8, 2 × M2 nuts, 2 × M2 flat washers |
| OEM horn 1 to printed middle-link adapter | 2 × M2×8, 2 × M2 nuts, 2 × M2 flat washers; use opposed lateral slots |
| OEM horn 2 to printed paddle adapter | 2 × M2×8, 2 × M2 nuts, 2 × M2 flat washers; use opposed lateral slots |
| Each OEM horn onto output spline | 1 × OEM center screw; 2 total. Datasheet calls for M2×4. Exact supplied screw count cannot be established from package photo. |
| Center screw fallback | Shorten and deburr 2 spare M2×8 screws from the same kit to the measured required length (nominal 4 mm); check engagement and bottoming. No additional purchase needed. |
| Battery | Printed guard plus 2 ties; feet carry strap tension, not the pouch |
| XIAO | Thin insulating plastic shim beneath PCB plus tie; restrain firmly for reliable IMU orientation |
| Switch | Thin insulating shim plus tie; capacitor insulated and secured beside it |

The standard FT90M spline is **20-tooth, approximately 3.95 mm**, not a standard-size 25T spline. Use the matching horns shown in the servo package photo. Their actual hole positions and stack height remain a CAD fit check. Drill two suitable horn holes to 2.2 mm to match the adapter slots; trim unused horn arms if needed. Do not drill the spline hub. The hardware pack includes 17 spare complete M2 sets before any center-screw fallback. Split lock washers are supplied but not required against the printed plastic.

## Materials already assumed at an equipped bench

These are explicit exclusions from the purchased-parts subtotal, not hidden robot components:

- Approximately 35–45 g PLA+/PETG including support/waste. Four robot prints: base, middle link, paddle, battery guard.
- Solder and flux; approximately 15 heat-shrink sleeves if already owned.
- Two small thin PET/Kapton insulating shims for PCB undersides, plus a small amount of insulating tape for exposed joints. Mounting must remain firm, not on thick soft foam.
- Wiring: supplied RCY pigtail plus shortened servo leads. Reuse servo-lead offcuts for controller BAT/GND and signal connections. Keep main battery/servo power connections short; use the supplied 20-AWG wire for the battery trunk. Allow moving service loops.
- USB-C **data** cable and ordinary USB 5 V source for programming/charging; laptop, printer, soldering tools, calipers, multimeter, small Phillips driver, 2.2 mm drill. A scale and current-limited supply/oscilloscope are useful for characterization.

Do not purchase a Raspberry Pi, PCA9685, separate IMU, buck/boost module, or extra LiPo charger for this architecture. Optional smaller batteries should be chosen only after confirming dimensions, connector, discharge rating and standard 4.2 V charge chemistry.
