"""Fit a provisional sensor-to-CAD rotation from two confirmed static poses.

Use .venv-sim/bin/python. No serial connection or robot commands.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import numpy as np
from imu import summarize


def fit_rotation(sensor_up_vectors, base_up_vectors):
    sensor = np.asarray(sensor_up_vectors, dtype=float)
    base = np.asarray(base_up_vectors, dtype=float)
    sensor = sensor / np.linalg.norm(sensor, axis=1, keepdims=True)
    base = base / np.linalg.norm(base, axis=1, keepdims=True)
    if np.linalg.matrix_rank(sensor, tol=.1) < 2 or np.linalg.matrix_rank(base, tol=.1) < 2:
        raise ValueError('At least two well-separated gravity directions are required.')
    u, _, vt = np.linalg.svd(sensor.T @ base)
    correction = np.diag([1., 1., np.linalg.det(vt.T @ u.T)])
    rotation = vt.T @ correction @ u.T
    residual = np.rad2deg(np.arccos(np.clip(np.sum((sensor @ rotation.T)*base, axis=1), -1., 1.)))
    assert np.allclose(rotation @ rotation.T, np.eye(3), atol=1e-6)
    assert np.isclose(np.linalg.det(rotation), 1.)
    return rotation, residual


def read_pose(path):
    with path.open(newline='') as handle:
        report = summarize(list(csv.DictReader(handle)))
    if not report['sensor_quality_check'] or not report['rough_stationary_check']:
        raise ValueError(f'{path}: clean stationary capture required.')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upright', type=Path, required=True)
    parser.add_argument('--horn-up', type=Path, required=True)
    parser.add_argument('--validate-inverted', type=Path, help='Independent upside-down check, excluded from fitting')
    parser.add_argument('--out', type=Path, default=Path('build/imu/mount_rotation_provisional.json'))
    args = parser.parse_args()
    if args.out.exists():
        parser.error('Choose a new output path; existing calibration is preserved.')
    paths = [args.upright, args.horn_up]
    reports = [read_pose(path) for path in paths]
    # CAD +Z is above the flat base. The lower output-horn bracket occupies
    # negative X in the final assembly; horn-side-up therefore measures -X UP.
    expected = [[0., 0., 1.], [-1., 0., 0.]]
    rotation, residual = fit_rotation([r['mean_accel_sensor_g'] for r in reports], expected)
    if max(residual) > 5.:
        raise ValueError(f'Pose alignment residual too large: {residual.tolist()} degrees.')
    count = sum(r['samples'] for r in reports)
    bias = sum(np.asarray(r['mean_gyro_sensor_rad_s'])*r['samples'] for r in reports)/count
    result = {
        'status': 'provisional; independent pose/rotation validation still required',
        'convention': 'base_vector = R_sensor_to_base @ sensor_vector; column vectors',
        'R_sensor_to_base': rotation.tolist(),
        'gyro_bias_candidate_sensor_rad_s': bias.tolist(),
        'gyro_correction_order': 'Subtract candidate bias in sensor axes, then rotate to base axes.',
        'fit_angular_residual_deg': residual.tolist(),
        'pose_definitions': ['Base flat and upright: accelerometer UP = base +Z.',
                             'Base vertical with lower output-horn side up: accelerometer UP = base -X.'],
        'captures': [{'file': str(p), 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                      'summary': r} for p,r in zip(paths,reports)],
        'accelerometer_bias_and_scale_calibrated': False,
        'dynamic_attitude_estimator_integrated': False,
        'applied_to_firmware': False,
        'limitation': 'Two static poses fit mounting rotation, not full accelerometer calibration; manual placement and sensor bias affect the fit.'
    }
    if args.validate_inverted:
        held_out = read_pose(args.validate_inverted)
        up = np.asarray(held_out['mean_accel_sensor_g'])
        up = rotation @ (up/np.linalg.norm(up))
        error = float(np.rad2deg(np.arccos(np.clip(up @ [0.,0.,-1.],-1.,1.))))
        result['independent_inverted_check'] = {
            'file': str(args.validate_inverted),
            'sha256': hashlib.sha256(args.validate_inverted.read_bytes()).hexdigest(),
            'used_for_fitting_or_bias': False,
            'measured_UP_in_base': up.tolist(), 'expected_UP_in_base': [0.,0.,-1.],
            'angle_error_deg': error, 'acceptance_threshold_deg': 5.,
            'status': 'passed' if error <= 5. else 'failed',
            'summary': held_out,
        }
        if error <= 5.:
            result['status'] = 'provisional static rotation; independent inverted check passed; dynamic validation pending'
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
