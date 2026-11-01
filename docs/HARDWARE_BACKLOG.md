# Hardware backlog

## Custom carrier PCB — user priority

Requested 31 October 2026. The user strongly prefers eliminating loose wiring and wants a custom PCB in a future hardware revision.

Candidate scope: carry the XIAO nRF52840 Sense, route battery positive/ground buses and D0/D1 servo signals on the PCB, and provide compact battery and two servo connectors. Fit the final printed base and leave access to USB-C. Evaluate direct castellated mounting versus a removable XIAO footprint. Revisit power isolation and charging connections as part of that design; no new charger or power architecture is selected here. Two short servo harnesses and a battery connection may remain unless their physical interfaces are redesigned.

PCB design and component selection are deferred to a future hardware revision; they are not required before the present simulation/training work.

## Current mass-model assumptions

At the user's instruction, ignore wiring mass for the first simulation mass model. Keep that exclusion explicit in mass records. The current model must not add an imaginary carrier PCB mass; the PCB belongs to a later physical revision.
