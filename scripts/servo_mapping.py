"""Offline conversion using reviewed visual calibration; no hardware access."""
import argparse
import json
import math
from pathlib import Path

DEFAULT = Path(__file__).resolve().parents[1] / 'firmware/servo_calibration/results/2026-11-02/visual_mapping.json'


def angle_to_pulse(calibration, joint, angle_deg):
    """Interpolate observed poses only. Reject extrapolation and unconfirmed signs."""
    if not math.isfinite(angle_deg):
        raise ValueError('Angle must be finite.')
    mapping = calibration['joints'][joint]
    if not mapping['sign_confirmed_from_user_direction']:
        raise ValueError('CAD direction is not confirmed.')
    knots = sorted(mapping['knots'], key=lambda row: row['angle_deg'])
    if len(knots) < 2:
        raise ValueError('At least two observed angles are required.')
    for left, right in zip(knots, knots[1:]):
        a, b = left['angle_deg'], right['angle_deg']
        u, v = left['pulse_us'], right['pulse_us']
        if not all(math.isfinite(x) for x in (a, b, u, v)) or b <= a or not (500 <= u <= 2500 and 500 <= v <= 2500):
            raise ValueError('Invalid calibration knots.')
        if (v - u) * mapping['CAD_pulse_sign'] <= 0:
            raise ValueError('Calibration direction is inconsistent or non-monotonic.')
    if angle_deg < knots[0]['angle_deg'] or angle_deg > knots[-1]['angle_deg']:
        raise ValueError('Angle lies outside the observed range; extrapolation is disabled.')
    for left, right in zip(knots, knots[1:]):
        if left['angle_deg'] <= angle_deg <= right['angle_deg']:
            fraction = (angle_deg - left['angle_deg']) / (right['angle_deg'] - left['angle_deg'])
            return round(left['pulse_us'] + fraction * (right['pulse_us'] - left['pulse_us']))
    raise ValueError('No interpolation segment found.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('joint', choices=['lower', 'upper'])
    parser.add_argument('angle_deg', type=float)
    parser.add_argument('--calibration', type=Path, default=DEFAULT)
    args = parser.parse_args()
    try:
        value = angle_to_pulse(json.loads(args.calibration.read_text()), args.joint, args.angle_deg)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps({'joint': args.joint, 'angle_deg': args.angle_deg, 'estimated_pulse_us': value,
                      'basis': 'Approximate visual static mapping; no motor command sent.'}, indent=2))


if __name__ == '__main__':
    main()
