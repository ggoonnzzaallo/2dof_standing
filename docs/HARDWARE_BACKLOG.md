# Hardware backlog

## Onboard RGB LED for battery status — future firmware idea

Requested by the user after the final-CAD simulator update. Revisit later; no firmware change or upload is part of this note.

Use the XIAO nRF52840 Sense's programmable RGB user LED, with the existing battery-voltage telemetry, to indicate battery status without adding components or wiring. See [Seeed's board documentation](https://wiki.seeedstudio.com/XIAO_BLE/). The separate charger indicator is not the programmable status LED. The current bench firmware does not assign the RGB LED an application status role.

Candidate behavior: green for adequate voltage, amber for getting low, and red/blinking red for low voltage or a battery-guard stop. Choose thresholds after ADC calibration and voltage-sag characterization; reuse the existing guard decisions rather than creating conflicting battery limits. Filter voltage readings and add hysteresis so servo load does not make the colors flicker. Use brief/dim indications where practical to limit LED power consumption, and update without blocking servo, IMU or policy timing.

Reserve higher-priority indications for faults or other essential robot states if needed. Keep bootloader behavior and the charger LED's existing function intact. Voltage indicates approximate charge/low-voltage status, not battery aging, capacity or precise state of charge; USB charging also affects the reading. The indicator supplements the existing motion guard and does not disconnect battery power.

## Custom carrier PCB — user priority

Requested 31 October 2026. The user strongly prefers eliminating loose wiring and wants a custom PCB in a future hardware revision.

Candidate scope: carry the XIAO nRF52840 Sense, route battery positive/ground buses and D0/D1 servo signals on the PCB, and provide compact battery and two servo connectors. Fit the final printed base and leave access to USB-C. Evaluate direct castellated mounting versus a removable XIAO footprint. Revisit power isolation and charging connections as part of that design; no new charger or power architecture is selected here. Two short servo harnesses and a battery connection may remain unless their physical interfaces are redesigned.

PCB design and component selection are deferred to a future hardware revision; they are not required before the present simulation/training work.

## Current mass-model assumptions

At the user's instruction, ignore wiring mass for the first simulation mass model. Keep that exclusion explicit in mass records. The current model must not add an imaginary carrier PCB mass; the PCB belongs to a later physical revision.
