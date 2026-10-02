# Procurement status — 1 October 2026

The user reports **all robot components ordered**. This records what is known from the conversation; it is not a delivery or inspection record. Do not reorder parts solely because a historical sourcing page still has purchase links.

| Component | Reported status | Evidence and remaining check |
|---|---|---|
| PTK 7465 MG servos, two | Ordered, per user | Exact listing, price, manufacturer suffix, included horns, center screws, spline, flange and body dimensions have not been supplied. Confirm these on receipt. Do not substitute the 7465W or MG-D identity silently. |
| E-flite EFLB5001S25, 500 mAh 1S 25C LiPo | Two ordered | User supplied a checkout image showing two units, $28.97 total with shipping. Check connector polarity and cell condition on arrival. One cell is used in the robot; the second is spare. |
| Pololu 2810 LV Mini MOSFET Slide Switch | Two ordered, backordered | User supplied a sales-order image showing two units. One is used; one is spare. |
| Pololu 2181 male JST-RCY lead | Two ordered, backordered | Same sales order. One is used; one is spare. The Pololu order total for both product lines was $23.44 with shipping and tax. |
| XIAO nRF52840 Sense and remaining consumables/fasteners | Ordered, per user's overall report | Exact seller, variant, quantities and paid amounts were not supplied. Verify the board says **Sense** and has the onboard IMU; check fasteners against the received servo ears and horns. |

The **known checkout totals** are $23.44 (Pololu) plus $28.97 (two batteries), or **$52.41**. This is not the project's total: servo, controller and remaining order costs are unknown. The original under-$100 goal cannot yet be assessed from recorded receipts. Do not publish personal details from order screenshots in this repository.

## Incoming checks before assembly

1. Photograph or measure the received PTK servo's label and dimensions, spline and supplied horn/center screw. Update `cad/build_cad.py` and regenerate the mounts before final printing. The existing CAD was sized for FT90M.
2. Confirm connector polarity with a multimeter before connecting the battery. Keep motor current off XIAO power traces; the battery feeds the XIAO and, separately through Pololu 2810, both servo power wires.
3. Characterize one servo, then both, at battery voltages near 4.2, 3.8 and 3.6 V. Record current, voltage sag, travel, unloaded and loaded step response, and whether a scripted rise succeeds. The reference robot's one-cell success is useful evidence, but the PTK servo is not guaranteed by a published 1S rating.
4. Update the servo ranges in `sim/` from the measured PTK data before substantial RL training. The existing FT90M numbers are placeholders and should not be treated as measured PTK performance.
5. Implement and verify firmware servo cutoff, USB charging interlock and charge-current configuration before relying on in-robot charging or unattended operation. These are still requirements, not finished features.
