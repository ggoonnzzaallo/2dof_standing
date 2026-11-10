# Documentation

[Project home](../README.md) · [Project summary and video facts](PROJECT_SUMMARY.md)

## Build and operate

| Guide | Contents |
|---|---|
| [Operating instructions](OPERATING_INSTRUCTIONS.md) | Battery-only startup, stopping, charging, inactivity and Mac controls |
| [BOM](../BOM.md) | Components, quantities, roles and purchase references |
| [Complete wiring](../electrical/FROM_SCRATCH.md) | Current Rev C connections, including D8/D7 PWM; [phone diagram](../electrical/REV_C_PHONE_WIRING.png), [schematic PDF](../electrical/REV_C_WIRING.pdf) |
| [Electrical design](../electrical/README.md) | Master-switch behavior, charging limits and commissioning |
| [Hardware reference](../HARDWARE.md) | Power, sensing, servo selection and measurement assumptions |
| [CAD guide](../cad/README.md) | Current complete STEP, printable enclosure and arm source |
| [Electronics enclosure](../cad/electronics_pod/README.md) | Current C3 cup, C2 lid, layouts, previews and printable files |
| [Print and fit checks](../cad/electronics_pod/PRINT_FIT_CHECK.md) | Enclosure assembly checks |

## Software and learning

| Guide | Contents |
|---|---|
| [Firmware setup](../firmware/README.md) | Mac/VS Code toolchain, build and upload commands |
| [Current controller](../firmware/policy_control/README.md) | Inference, limits, operating modes, telemetry and supervised trials |
| [Simulation guide](../sim/README.md) | Current interactive playground, setup and experiment navigation |
| [Filming the simulation](FILMING_SIMULATION.md) | Repeatable timed pushes, restart/pause keys and portrait MP4 export |
| [Current C3 training and results](../sim/enclosure_c3/upright/README.md) | PPO checkpoint, success definition, held-out evaluation and joint-clearance calculations |
| [Controller development history](../firmware/policy_control/HISTORY.md) | Dated firmware releases and physical observations |
| [Validation log](../firmware/VALIDATION.md) | Chronological builds, captures and checks |

## Design decisions and future work

- [Controller and onboard IMU](CONTROLLER_DECISION.md) · [Servo feedback tradeoff](SERVO_DECISION.md).
- [Calibration plan and earlier measurements](SIM_CALIBRATION_PLAN.md) · [Original mass accounting](../sim/mass_properties/README.md).
- [Persistent recovery and personality](RECOVERY_BEHAVIOR.md) · [Hardware backlog and battery LED idea](HARDWARE_BACKLOG.md) · [Integrated controller PCB](INTEGRATED_CONTROLLER_PCB.md).

## Historical references

These record earlier choices and experiments; use the guides above for the installed build.

- **Purchasing:** [procurement records](PROCUREMENT_STATUS.md), [AliExpress sourcing](ALIEXPRESS_SOURCING.md), [DigiKey sourcing](DIGIKEY_SOURCING.md), [superseded FT90M BOM](FT90M_BOM_HISTORY.md). Receipt coverage is incomplete; the original under-$100 target is not a verified delivered cost.
- **Bench firmware:** [Rev B servo/dance guide](../firmware/BENCH_GUIDE.md), [IMU commissioning](../firmware/imu_bench/README.md), [servo calibration](../firmware/servo_calibration/README.md), [policy shadow](../firmware/policy_shadow/README.md), [arithmetic probe](../firmware/policy_probe/README.md).
- **Older wiring:** [Rev A diagram](../electrical/REV_A_WIRING.pdf), [Rev B direct-power notes](../electrical/REV_B_NOTES.md).
- **Older simulation:** [original starter](../sim/STARTER_GUIDE.md), [original recovery experiment](../sim/recovery/README.md), [C2 enclosure](../sim/enclosure/README.md), [first C3 actor / 0.7](../sim/enclosure_c3/README.md), [robust C3 / 0.8](../sim/enclosure_c3/robust/README.md). Scores use different geometry and success criteria; they are not one hardware reliability series.

Raw captures, CAD inputs, checkpoints and source hashes remain with their respective experiments.
