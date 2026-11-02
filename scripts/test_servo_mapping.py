"""Check real calibration provenance and reject unsupported actuation conversions."""
import copy
import csv
import hashlib
import json
import math
import unittest
from servo_mapping import DEFAULT, angle_to_pulse


class MappingTests(unittest.TestCase):
    def setUp(self):
        self.mapping = json.loads(DEFAULT.read_text())

    def test_raw_observations_back_each_knot(self):
        for name, digest in self.mapping['raw_sha256'].items():
            self.assertEqual(hashlib.sha256((DEFAULT.parent / name).read_bytes()).hexdigest(), digest)
        session = json.loads((DEFAULT.parent / self.mapping['raw_session']).read_text())
        with (DEFAULT.parent / 'visual_session.csv').open(newline='') as source:
            rows = list(csv.DictReader(source))
        for joint, data in self.mapping['joints'].items():
            for knot in data['knots']:
                point = next(p for p in session['observations'] if p['joint_name'] == joint and p['t_ms'] == knot['sample_t_ms'])
                self.assertEqual(point['pulse_us'], knot['pulse_us'])
                self.assertEqual(point['visual_angle_deg'], knot['angle_deg'])
                self.assertTrue(any(int(r['t_ms']) == point['t_ms'] and int(r['joint']) == point['joint'] and int(r['pulse_us']) == point['pulse_us'] and int(r['target_us']) == point['pulse_us'] for r in rows))

    def test_observed_poses_and_between_pose_conversion(self):
        for joint in ('lower', 'upper'):
            for angle, pulse in [(-45, 1900), (0, 1500), (45, 1100), (22.5, 1300), (-22.5, 1700)]:
                self.assertEqual(angle_to_pulse(self.mapping, joint, angle), pulse)
            pulses = [angle_to_pulse(self.mapping, joint, d) for d in range(-45, 46)]
            self.assertTrue(all(a > b for a, b in zip(pulses, pulses[1:])))

    def test_outside_range_and_unreviewed_sign_are_refused(self):
        for angle in (-90, -80, -45.01, 45.01, 80, 90, math.nan, math.inf):
            with self.assertRaises(ValueError):
                angle_to_pulse(self.mapping, 'lower', angle)
        bad = copy.deepcopy(self.mapping)
        bad['joints']['lower']['sign_confirmed_from_user_direction'] = False
        with self.assertRaises(ValueError):
            angle_to_pulse(bad, 'lower', 0)
        bad = copy.deepcopy(self.mapping)
        bad['joints']['lower']['knots'][1]['pulse_us'] = 2000
        with self.assertRaises(ValueError):
            angle_to_pulse(bad, 'lower', 0)


if __name__ == '__main__':
    unittest.main()
