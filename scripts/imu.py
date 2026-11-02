"""Record sensor-only XIAO telemetry; never sends motor commands.

Run with .tools/arduino/python/bin/python scripts/imu.py --out build/imu/upright.csv
"""
import argparse
import csv
import json
import math
from pathlib import Path
import statistics
import time

FIELDS = 't_us,ax_g,ay_g,az_g,gx_rad_s,gy_rad_s,gz_rad_s,acc_norm_g,battery_mv,sample_seq,i2c_errors,saturated,age_us'.split(',')


def wait_ready(device, timeout=5.):
    # Opening CDC can catch the tail of the automatic banner. Require a whole
    # response beginning with a version line; retry status rather than trusting
    # the first "Commands" line that happens to arrive.
    deadline = time.monotonic()+timeout
    next_request = 0.
    banner = []
    stopped = False
    while time.monotonic() < deadline:
        if time.monotonic() >= next_request:
            device.write(b'off\nstatus\n')
            next_request = time.monotonic()+.5
        line = device.readline().decode('ascii', errors='replace').strip()
        if line.startswith('OFF.'):
            stopped = True
            banner = []
        elif line.startswith('ROBOT ') and stopped:
            banner = [line]
        elif line and banner:
            banner.append(line)
        if 'Commands: status, sample, stream' in line and banner:
            break
    if 'ROBOT IMU BENCH 0.4' not in banner or 'IMU_READY: 1' not in banner:
        raise RuntimeError('Expected IMU firmware/ready sensor not found.\n'+'\n'.join(banner))
    return banner


def summarize(rows):
    if len(rows) < 20:
        raise ValueError('Need at least 20 valid samples.')
    mean = lambda key: statistics.mean(float(r[key]) for r in rows)
    sd = lambda key: statistics.stdev(float(r[key]) for r in rows)
    a = [mean(k) for k in FIELDS[1:4]]
    gyro = [mean(k) for k in FIELDS[4:7]]
    norm = math.sqrt(sum(v*v for v in a))
    dt = [((int(b['t_us'])-int(a['t_us'])) % (2**32))/1e6 for a,b in zip(rows,rows[1:])]
    positive = [d for d in dt if d > 0]
    clean = (not any(int(r['saturated']) for r in rows)
             and int(rows[0]['i2c_errors']) == int(rows[-1]['i2c_errors'])
             and max(int(r['age_us']) for r in rows) < 20000
             and all(0 < d <= .04 for d in dt))
    stationary = (.85 < norm < 1.15 and max(sd(k) for k in FIELDS[1:4]) < .03
                  and math.sqrt(sum(v*v for v in gyro)) < .15
                  and max(sd(k) for k in FIELDS[4:7]) < .05)
    return {'samples': len(rows), 'mean_accel_sensor_g': a,
            'accel_std_sensor_g': [sd(k) for k in FIELDS[1:4]],
            'mean_gyro_sensor_rad_s': gyro,
            'gyro_std_sensor_rad_s': [sd(k) for k in FIELDS[4:7]],
            'mean_accel_norm_g': mean('acc_norm_g'),
            'median_sample_interval_s': statistics.median(positive) if positive else None,
            'duplicate_sample_rows': sum(d == 0 for d in dt),
            'sample_gaps_over_40ms': sum(d > .04 for d in dt),
            'sensor_quality_check': clean,
            'max_sample_age_us': max(int(r['age_us']) for r in rows),
            'saturated_rows': sum(int(r['saturated']) != 0 for r in rows),
            'i2c_error_count_start': int(rows[0]['i2c_errors']),
            'i2c_error_count_end': int(rows[-1]['i2c_errors']),
            'battery_min_mv': min(int(r['battery_mv']) for r in rows),
            'battery_max_mv': max(int(r['battery_mv']) for r in rows),
            'rough_stationary_check': stationary,
            'static_DOWN_sensor_estimate': [-v/norm for v in a] if stationary else None,
            'note': 'Sensor axes only. Stationary heuristic is not calibration; acceleration during motion is not gravity.'}


def record(port, seconds, out, label):
    import serial
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() or out.with_suffix('.json').exists():
        raise FileExistsError(f'Choose a new output filename; preserving {out}.')
    rows = []
    with serial.Serial(port, 115200, timeout=.25, write_timeout=1) as device:
        try:
            banner = wait_ready(device)
            device.reset_input_buffer()
            device.write(b'stream\n')
            started = time.monotonic()
            got_header = False
            with out.open('x', newline='') as handle:
                writer = csv.DictWriter(handle, fieldnames=FIELDS)
                writer.writeheader()
                while time.monotonic()-started < seconds:
                    line = device.readline().decode('ascii', errors='replace').strip()
                    if not line:
                        continue
                    if line == ','.join(FIELDS):
                        got_header = True
                        continue
                    if line.startswith('ERROR:') or (got_header and line.startswith('OFF.')):
                        raise RuntimeError(line)
                    if not got_header:
                        continue
                    values = line.split(',')
                    if len(values) != len(FIELDS) or not all(math.isfinite(float(v)) for v in values):
                        raise ValueError(f'Invalid telemetry row: {line}')
                    row = dict(zip(FIELDS, values))
                    writer.writerow(row)
                    rows.append(row)
            summary = summarize(rows)
            summary.update({'label': label, 'requested_seconds': seconds, 'physical_motor_commands_sent': False})
            out.with_suffix('.json').write_text(json.dumps(summary, indent=2)+'\n')
            print(json.dumps(summary, indent=2))
            print(f'Saved {out} and {out.with_suffix(".json")}')
        finally:
            if device.is_open:
                try:
                    device.write(b'!\noff\n')
                except serial.SerialException:
                    pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port')
    parser.add_argument('--seconds', type=float, default=10.)
    parser.add_argument('--out', type=Path, default=Path('build/imu/upright.csv'))
    parser.add_argument('--label', default='unlabeled')
    parser.add_argument('--analyze', type=Path, help='Analyze an existing CSV without opening serial')
    args = parser.parse_args()
    if args.analyze:
        with args.analyze.open(newline='') as handle:
            print(json.dumps(summarize(list(csv.DictReader(handle))), indent=2))
        return
    if not 1 <= args.seconds <= 25:
        parser.error('--seconds must be 1..25; firmware stream limit is 30 s.')
    from serial.tools import list_ports
    ports = [p.device for p in list_ports.comports() if p.vid == 0x2886 and p.pid == 0x8045]
    if args.port:
        if args.port not in ports:
            parser.error('--port must identify a classic XIAO Sense application USB device.')
        port = args.port
    elif len(ports) == 1:
        port = ports[0]
    else:
        parser.error('Connect exactly one XIAO nRF52840 Sense, or provide --port.')
    record(port, args.seconds, args.out, args.label)


if __name__ == '__main__':
    main()
