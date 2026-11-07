# Hardware backlog

V1 is wrapped as a working prototype. The items below are optional future iterations/characterization, not uncompleted promises to add hardware to this build. See [project summary](PROJECT_SUMMARY.md).

## Onboard RGB LED for battery status — future firmware idea

Requested by the user after the final-CAD simulator update. Revisit later; no firmware change or upload is part of this note.

Use the XIAO nRF52840 Sense's programmable RGB user LED, with the existing battery-voltage telemetry, to indicate battery status without adding components or wiring. See [Seeed's board documentation](https://wiki.seeedstudio.com/XIAO_BLE/). The separate charger indicator is not the programmable status LED. The current bench firmware does not assign the RGB LED an application status role.

Candidate behavior: green for adequate voltage, amber for getting low, and red/blinking red for low voltage or a battery-guard stop. Choose thresholds after ADC calibration and voltage-sag characterization; reuse the existing guard decisions rather than creating conflicting battery limits. Filter voltage readings and add hysteresis so servo load does not make the colors flicker. Use brief/dim indications where practical to limit LED power consumption, and update without blocking servo, IMU or policy timing.

Reserve higher-priority indications for faults or other essential robot states if needed. Keep bootloader behavior and the charger LED's existing function intact. Voltage indicates approximate charge/low-voltage status, not battery aging, capacity or precise state of charge; USB charging also affects the reading. The indicator supplements the existing motion guard and does not disconnect battery power.

## Integrated controller and power PCB — user priority

**Expanded 3 November 2026:** replace the XIAO and Pololu modules with one custom PCB, including a lower-cost processor, onboard IMU, USB charging, genuine power isolation and direct servo connectors. See the [feasibility, cost targets and future development plan](INTEGRATED_CONTROLLER_PCB.md). This is a future iteration, not a change to the current Rev C wiring or purchasing BOM.

### Earlier carrier-only concept

Requested 31 October 2026. The user strongly prefers eliminating loose wiring and wants a custom PCB in a future hardware revision.

Candidate scope: carry the XIAO nRF52840 Sense, route battery positive/ground buses and servo signals (now lower D8 / upper D7) on the PCB, and provide compact battery and two servo connectors. Fit the final printed base and leave access to USB-C. Evaluate direct castellated mounting versus a removable XIAO footprint. Revisit power isolation and charging connections as part of that design; no new charger or power architecture is selected here. Two short servo harnesses and a battery connection may remain unless their physical interfaces are redesigned.

PCB design and component selection are deferred to a future hardware revision; they are not required before the present simulation/training work.

## Current mass-model assumptions

At the user's instruction, ignore wiring mass for the first simulation mass model. Keep that exclusion explicit in mass records. The current model must not add an imaginary carrier PCB mass; the PCB belongs to a later physical revision.


## Contact correction — implemented in the offline C2 model

At the user's request, replace the current base–middle and middle–upper whole-body contact exclusions with geometry/selective contact rules that allow intended pivot mating but detect real adjacent-link clashes. Audit the full joint envelope and dynamic motion, regenerate affected demonstrations, and retrain/evaluate with the real observation pipeline. Details are in [the calibration/training plan](SIM_CALIBRATION_PLAN.md#required-correction-at-the-next-training-pass--2-november-2026). This was implemented before the [C2 enclosure training pass](../sim/enclosure/README.md#contacts), using selective pivot-interface masks and active adjacent-body contacts. The older model/deployed actor retain their original exclusions, and continuous physical clearance is not established by the sampled model checks.
