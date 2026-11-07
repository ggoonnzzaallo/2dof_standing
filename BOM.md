# V1 build BOM — PTK 7465 MG, one Pololu

Current documented build, 7 November 2026. Parts have been assembled and operated; original purchase records are in [procurement history](docs/PROCUREMENT_STATUS.md). This table describes the final architecture. Earlier generated bearing/pin concepts are not a confirmed as-built shopping list.

| Component | Used in one robot | What it does | Recorded source/status |
|---|---:|---|---|
| PTK 7465 MG, three-wire positional servo | 2 | Drives the lower and upper joint. Internal position control, ordinary PWM commands; no position telemetry to the XIAO. | Purchased and physically operated. Exact seller and delivered price were not recorded. Same model family as the [reference robot](https://homemadegarbage.com/rl13). |
| Seeed XIAO nRF52840 Sense, SKU 102010469 | 1 | Runs the actor and PWM. Its onboard IMU senses base motion; ADC estimates battery voltage; USB-C charger charges the cell. | Purchased and firmware uploaded. Headers removed; direct soldered wires. [Manufacturer guide](https://wiki.seeedstudio.com/XIAO_BLE/). |
| E-flite EFLB5001S25, 500 mAh 1S 25C LiPo, JST-RCY | 1 | Supplies the controller and both servos. | Two purchased; one spare. Recorded two-pack order: **$28.97 delivered**. [Manufacturer listing](https://www.horizonhobby.com/product/1s-3.7v-500mah-25c-li-po-battery-jst-rcy/EFLB5001S25.html). |
| Pololu 2810 LV Mini MOSFET Slide Switch | 1 | Disconnects battery positive from the shared controller/servo bus. | Two purchased; one packaged, one spare. [Pololu documentation](https://www.pololu.com/product/2810). ON/SW pads unused. |
| Pololu 2181 male JST-RCY lead, 10 cm | 1 | Battery mating lead: positive to Pololu VIN, negative to common ground. | Two purchased; one spare. [Product](https://www.pololu.com/product/2181). Combined switch/lead order: **$23.44 delivered**. |
| Final printed arm parts | 1 set | Base/lid servo frame, middle structure and horn bracket, upper structure and horn bracket. | Use the [user's final Onshape geometry](cad/onshape_import/README.md), not the older generated concept. |
| Under-base cup and lid | 1 each | Locates battery, XIAO and Pololu; contains wiring and exposes USB/slider. | [C3 print ZIP](cad/electronics_pod/rev_c3_print_fit.zip): reprint cup only if retaining C2 lid. C2 fit approved; separate C3 approval not recorded. |
| M2×10 screws, self-tapped into plastic | 2 for enclosure | Attaches lid to cup; no nuts or inserts. | User-confirmed existing hardware; 2.0 mm blind bores match the working model baseline. |
| Servo/horn mounting screws and OEM horn center screws | Existing arm set | Secures servo bodies, printed horn brackets and supplied horns. | Already assembled. Exact final count/lengths outside the enclosure were not inventoried; do not substitute the old concept's fastener estimate. |
| Thin insulating PSA | As needed | Holds the PCBs on low lands and locates the battery without compressing its pouch. | Bench supply; boards use locating stops. |
| Insulated wire, solder, flux and heat shrink | As needed | Four-way switched-positive bus J1, five-way ground bus J2 and two PWM signal paths. | [Complete twelve-branch wiring](electrical/FROM_SCRATCH.md). Keep motor current off XIAO PCB power traces. |
| USB-C data/power cable | 1 | Programming, optional Mac controls and onboard charging. | Existing bench cable; plug must seat through the enclosure aperture. |

Lower servo signal is **D8 / 8**; upper is **D7 / 7**. Neither servo is supplied from XIAO 3V3 or VBUS. No external IMU, boost converter, servo-driver board or separate charger is part of this build. Capacitors/resistors were diagnostic options, not required installed parts.

The confirmed order totals sum to **$52.41**, including spare items. Controller, servo and miscellaneous delivered costs are missing, so the original **under-$100 target is not a verified final total**. Prices above are historical receipts, not current offers.

## Historical concept parts

Two MR83ZZ bearings and two 3×12 mm dowel pins were proposed for an early generated opposed-pivot design. Their purchase/use was never confirmed. They are not assumed to be in the final Onshape build, and the old generated arm/coupons are retained as [historical CAD](cad/README.md). Likewise, the earlier FT90M estimate is [historical](docs/FT90M_BOM_HISTORY.md).

## Power and charging

One cell directly supplies both servos through the Pololu and bus. Physical operation has been demonstrated, but rated 1S servo performance, load/current margins and full charge termination through the switch remain uncharacterized. Software PWM-off does not remove servo idle load. Use [operating instructions](docs/OPERATING_INSTRUCTIONS.md) for battery-only automatic startup, USB-at-boot charging and full OFF.
