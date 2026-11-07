"""Supervise the onboard recovery policy, or its no-PWM shadow mode.

Default execution arms both servos, holds nominal neutral, then runs the actor.
Use --shadow for USB-only commissioning with battery and servo plugs disconnected.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import time
from shadow import HostActor

ROOT = Path(__file__).resolve().parents[1]
LIMIT = 1.3962634016
BANNER = 'ROBOT POLICY CONTROL 0.5'
SUPPORTED_BANNERS = {BANNER, 'ROBOT POLICY CONTROL 0.4'}


def handshake(device, require_ready=True):
    lines = []
    stopped = False
    end = time.monotonic() + 8
    next_request = 0
    while time.monotonic() < end:
        if time.monotonic() >= next_request:
            device.write(b'off\nstatus\n')
            next_request = time.monotonic() + .6
        line = device.readline().decode('ascii', errors='replace').strip()
        if line.startswith('ROBOT POLICY CONTROL ') and line not in SUPPORTED_BANNERS:
            raise RuntimeError('D8 lower / D7 upper wiring requires controller firmware 0.4. Upload the updated controller before arming or charging. Received: ' + line)
        if line.startswith('OFF.'):
            stopped = True
            lines = []
        elif line in SUPPORTED_BANNERS and stopped:
            lines = [line]
        elif lines and line:
            lines.append(line)
        if line == 'READY' and require_ready and 'INACTIVITY_LOCKED: 1' in lines:
            raise RuntimeError('IMU inactivity lock: reboot the XIAO before arming. Charging remains available.')
        required = ['IMU_READY: 1', 'FILTER_READY: 1'] if require_ready else []
        disarmed = 'MODE: 0' in lines or (not require_ready and 'MODE: 6' in lines)
        if line == 'READY' and disarmed and lines and lines[0] in SUPPORTED_BANNERS and all(v in lines for v in required):
            return lines
    raise RuntimeError('Expected a ready, disarmed learned controller.\n' + '\n'.join(lines))


def analyze(rows, actor, shadow):
    if len(rows) < 20:
        raise ValueError('Insufficient telemetry: at least 20 policy frames required.')
    parity = history = integration = norm_error = pulse_error = 0.
    prior = None
    for row in rows:
        values = {k: int(v) for k, v in row.items()}
        if values['mode'] != (3 if shadow else 2):
            raise ValueError('Unexpected controller mode.')
        obs = [values[f'obs{i}_u6'] / 1e6 for i in range(10)]
        action = [values[f'action{i}_u6'] / 1e6 for i in range(2)]
        target = [values[f'target{i}_urad'] / 1e6 for i in range(2)]
        if max(map(abs, obs + action)) > 1.000001 or max(map(abs, target)) > LIMIT + 1e-6:
            raise ValueError('Observation, action or target out of contract bounds.')
        parity = max(parity, max(abs(a - b) for a, b in zip(actor.predict(obs), action)))
        norm_error = max(norm_error, abs(math.sqrt(sum(v*v for v in obs[:3])) - 1))
        if values['frame'] == 1:
            history = max(history, *map(abs, obs[6:]))
        if prior and values['frame'] == int(prior['frame']) + 1:
            for i in range(2):
                history = max(history, abs(obs[6+i] - int(prior[f'target{i}_urad']) / 1e6 / LIMIT),
                              abs(obs[8+i] - int(prior[f'action{i}_u6']) / 1e6))
        for i in range(2):
            expected = max(-LIMIT, min(LIMIT, obs[6+i] * LIMIT + .06 * action[i]))
            integration = max(integration, abs(expected - target[i]))
            pwm = values[f'pwm{i}_us']
            if shadow:
                if pwm != 0:
                    raise ValueError('Shadow mode reported an active PWM output.')
            else:
                if not 789 <= pwm <= 2211:
                    raise ValueError('PWM outside deployment envelope.')
                pulse_error = max(pulse_error, abs(pwm - round(1500 - 509.29581789406507 * target[i])))
        prior = row
    if parity > .001 or history > 5e-6 or integration > 5e-6 or norm_error > 1e-4 or pulse_error > 1:
        raise ValueError(f'Contract check failed: parity={parity}, history={history}, integration={integration}, norm={norm_error}, pulse={pulse_error}')
    return {'contract_checks': 'passed', 'frames_logged': len(rows), 'last_frame': int(rows[-1]['frame']),
            'mode': 'no-PWM shadow' if shadow else 'physical PWM control',
            'MCU_vs_host_max_action_error_from_quantized_observations': parity,
            'history_max_error': history, 'target_integration_max_error_rad': integration,
            'unit_DOWN_max_norm_error': norm_error, 'PWM_mapping_max_rounding_difference_us': pulse_error,
            'inference_median_us': statistics.median(int(r['inference_us']) for r in rows),
            'inference_max_us': max(int(r['inference_us']) for r in rows),
            'deadline_lateness_max_us': max(int(r['late_us']) for r in rows),
            'sample_age_max_us': max(int(r['sample_age_us']) for r in rows),
            'i2c_errors_start_end': [int(rows[0]['i2c_errors']), int(rows[-1]['i2c_errors'])],
            'dropped_telemetry': int(rows[-1]['dropped']),
            'battery_node_min_max_mv': [min(int(r['battery_mv']) for r in rows), max(int(r['battery_mv']) for r in rows)],
            'maximum_commanded_angle_deg': max(abs(int(r[f'target{i}_urad'])) / 1e6 * 180 / math.pi for r in rows for i in range(2)),
            'limitation': 'Telemetry confirms numerical commands, not actual shaft angles or physical recovery.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port')
    parser.add_argument('--seconds', type=float, default=15)
    parser.add_argument('--shadow', action='store_true')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--analyze', type=Path)
    args = parser.parse_args()
    if not 1 <= args.seconds <= 45:
        parser.error('--seconds must be between 1 and 45.')
    actor = HostActor()
    try:
        if args.analyze:
            with args.analyze.open(newline='') as source:
                print(json.dumps(analyze(list(csv.DictReader(source)), actor, args.shadow), indent=2))
            return
        if args.out is None:
            parser.error('--out is required for a new recording.')
        import serial
        from serial.tools import list_ports
        ports = [p.device for p in list_ports.comports() if p.vid == 0x2886 and p.pid == 0x8045]
        if args.port and args.port not in ports:
            parser.error('--port must identify the classic XIAO Sense application.')
        if not args.port and len(ports) != 1:
            parser.error('Connect exactly one classic XIAO Sense or specify --port.')
        paths = [args.out, args.out.with_suffix('.csv'), args.out.with_suffix('.txt')]
        if len(set(paths)) != 3 or any(path.exists() for path in paths):
            parser.error('Choose a new .json output filename; captures are never overwritten.')
        args.out.parent.mkdir(parents=True, exist_ok=True)
        report = {'requested_seconds': args.seconds, 'shadow': args.shadow,
                  'physical_motor_commands_requested': not args.shadow,
                  'trained_range_deg': [-80, 80], 'angle_mapping': 'Linear extrapolation of visually measured +/-45 deg references, explicitly authorized by user.',
                  'actor_header_sha256': hashlib.sha256((ROOT/'sim/recovery/results/policy_simulation_only.h').read_bytes()).hexdigest()}
        rows = []
        error = None
        with serial.Serial(args.port or ports[0], 115200, timeout=.04, write_timeout=1) as device:
            try:
                report['firmware_banner'] = handshake(device)
                device.reset_input_buffer()
                with paths[1].open('x', newline='') as capture, paths[2].open('x') as log:
                    writer = None
                    keep_at = 0

                    def read_line():
                        nonlocal keep_at
                        if time.monotonic() >= keep_at:
                            device.write(b'keep\n')
                            keep_at = time.monotonic() + .25
                        line = device.readline().decode('ascii', errors='replace').strip()
                        if line:
                            log.write(line + '\n')
                            log.flush()
                        if line.startswith(('OFF', 'REFUSED', 'ERROR')):
                            raise RuntimeError(line)
                        return line

                    if not args.shadow:
                        device.write(b'arm\n')
                        end = time.monotonic() + 3
                        armed = False
                        while time.monotonic() < end:
                            if read_line().startswith('ARMED:'):
                                armed = True
                                break
                        if not armed:
                            raise RuntimeError('Arm acknowledgement missing.')
                        end = time.monotonic() + 1.2
                        while time.monotonic() < end:
                            read_line()
                    device.write(b'shadow\n' if args.shadow else b'run\n')
                    started = time.monotonic()
                    last_data = started
                    fields = None
                    print('SHADOW recording; no PWM.' if args.shadow else 'POLICY RUNNING: trained +/-80 degrees. Ctrl+C stops PWM.', flush=True)
                    while time.monotonic() - started < args.seconds:
                        line = read_line()
                        if line.startswith('frame,t_us,mode,'):
                            fields = line.split(',')
                            writer = csv.DictWriter(capture, fieldnames=fields, lineterminator='\n')
                            writer.writeheader()
                        elif line.startswith('D,'):
                            if not writer:
                                raise ValueError('Telemetry arrived before its header.')
                            values = line.split(',')[1:]
                            if len(values) != len(fields):
                                raise ValueError('Malformed policy telemetry.')
                            row = dict(zip(fields, values))
                            for value in values:
                                int(value)
                            if int(row['mode']) != (3 if args.shadow else 2):
                                raise ValueError('Unexpected controller mode.')
                            writer.writerow(row)
                            capture.flush()
                            rows.append(row)
                            last_data = time.monotonic()
                        if time.monotonic() - last_data > .5:
                            raise RuntimeError('Telemetry missing for over 500 ms; stopping.')
            except KeyboardInterrupt:
                error = 'Interrupted by user.'
            except (RuntimeError, ValueError, OSError, serial.SerialException) as exc:
                error = str(exc)
            finally:
                try:
                    device.write(b'!\noff\n')
                    end = time.monotonic() + .4
                    while time.monotonic() < end:
                        line = device.readline().decode('ascii', errors='replace').strip()
                        if line.startswith('OFF'):
                            report['stop_acknowledgement'] = line
                            break
                except (OSError, serial.SerialException) as exc:
                    report['stop_write_error'] = str(exc)
        try:
            report.update(analyze(rows, actor, args.shadow))
        except ValueError as exc:
            report['contract_checks'] = 'failed or insufficient data'
            error = error or str(exc)
        report['status'] = 'stopped_early' if error else 'completed'
        if error:
            report['error'] = error
        if paths[1].exists():
            report['CSV_sha256'] = hashlib.sha256(paths[1].read_bytes()).hexdigest()
        args.out.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2), flush=True)
        if error:
            raise SystemExit(1)
    finally:
        actor.close()


if __name__ == '__main__':
    main()
