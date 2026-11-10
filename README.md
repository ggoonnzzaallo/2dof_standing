# Two-DOF self-righting robot

A small, 3D-printed robot that learns to get back upright using two servo joints, an onboard IMU and a neural controller. It runs from a single LiPo cell without a computer.

Inspired by [Homemade Garbage's robot](https://homemadegarbage.com/rl13) and [SelfRisingRobot](https://github.com/homemadegarbage/SelfRisingRobot).

The build uses a **XIAO nRF52840 Sense**, two **PTK 7465 MG servos**, a **500 mAh 1S LiPo** and one **Pololu battery switch**, packaged in a printed base enclosure. MuJoCo and Stable-Baselines3 PPO supply the trained controller.

**Latest release: controller 0.9 / C3 enclosure, 7 November 2026.** Includes ±90° recovery, straight-arm holding on a level base, automatic battery-only startup and a one-minute inactivity stop. Uploaded; physical recovery with this release awaits confirmation. See [results and limitations](sim/enclosure_c3/upright/README.md).

| I want to… | Start here |
|---|---|
| Run, stop or charge the robot | [Operating instructions](docs/OPERATING_INSTRUCTIONS.md) |
| Buy parts and wire the electronics | [BOM](BOM.md) · [Complete wiring](electrical/FROM_SCRATCH.md) |
| Print or inspect the CAD | **[Current complete STEP](cad/assembly.step)** · [Enclosure STL package](cad/electronics_pod/rev_c3_print_fit.zip) · [CAD guide](cad/README.md) |
| Open the simulation or understand training | [Simulation guide](sim/README.md) |
| Build or upload firmware | [Firmware setup](firmware/README.md) |
| Understand the project or find detailed records | [Project summary](docs/PROJECT_SUMMARY.md) · [Documentation index](docs/README.md) |
