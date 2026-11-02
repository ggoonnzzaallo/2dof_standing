"""Interactive, supervised pulse/visual-angle recorder; never moves at startup.

Use .tools/arduino/python/bin/python scripts/calibrate_servos.py --out build/calibration/session_01.json
"""
import argparse
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import select
import sys
import time

BANNER = 'ROBOT SERVO CALIBRATION 0.1'
HELP = '''Commands:
  lower / upper     Start one joint at nominal 1500 us; support both links.
  + / -             Nudge target by 25 us (not degrees).
  pulse N           Set target, at most 50 us from the preceding target.
  mark DEG [note]   Save a visually estimated angle once pulse has settled.
  window MIN MAX    Change pulse envelope while OFF; default 1000..2000 us.
  status / off      Inspect or stop PWM; battery power remains live.
  quit              Stop PWM and close the session.
Straight = 0 degrees; bends may be marked +45/-45 or +90/-90.
Angle signs are provisional until checked against CAD. Do not force 90 degrees
through a mechanical stop. These are approximate visual observations, not encoders.
'''


def handshake(device):
    lines = []
    stopped = False
    deadline = time.monotonic() + 5
    request_at = 0
    while time.monotonic() < deadline:
        if time.monotonic() >= request_at:
            device.write(b'off\nstatus\n')
            request_at = time.monotonic() + .7
        line = device.readline().decode('ascii', errors='replace').strip()
        if line.startswith('OFF.'):
            stopped = True
            lines = []
        elif line == BANNER and stopped:
            lines = [line]
        elif lines:
            lines.append(line)
        if line == 'READY' and lines:
            if 'ACTIVE_JOINT: -1' in lines and any(s.startswith('REV_B_DIRECT:') for s in lines):
                return lines
    raise RuntimeError('Expected stopped calibration firmware.\n' + '\n'.join(lines))


def parse_data(line):
    values = line.split(',')
    if len(values) != 6 or values[0] != 'DATA':
        return None
    t, joint, target, pulse, battery = map(int, values[1:])
    if joint not in (-1, 0, 1) or not 500 <= target <= 2500 or not 500 <= pulse <= 2500:
        raise ValueError('Invalid calibration telemetry: ' + line)
    return {'t_ms': t, 'joint': joint, 'target_us': target, 'pulse_us': pulse, 'battery_mv': battery}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port')
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    import serial
    from serial.tools import list_ports
    ports = [p.device for p in list_ports.comports() if p.vid == 0x2886 and p.pid == 0x8045]
    if args.port and args.port not in ports:
        parser.error('--port must identify the classic XIAO Sense application.')
    if not args.port and len(ports) != 1:
        parser.error('Connect exactly one classic XIAO Sense or specify --port.')
    paths = [args.out, args.out.with_suffix('.csv'), args.out.with_suffix('.txt')]
    if len(set(paths)) != 3 or any(path.exists() for path in paths):
        parser.error('Use a new .json output filename; capture files are never overwritten.')
    args.out.parent.mkdir(parents=True, exist_ok=True)
    session = {'created_utc': datetime.now(timezone.utc).isoformat(), 'firmware': BANNER,
               'method': 'Approximate visual angles chosen by the operator, relative to parent link.',
               'angle_convention': 'Straight = 0 deg. Signed viewing direction provisional; CAD sign not confirmed.',
               'CAD_sign_confirmed': {'lower': False, 'upper': False},
               'physical_limits_confirmed': False, 'observations': [], 'events': []}

    def save():
        temporary = args.out.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(session, indent=2) + '\n')
        temporary.replace(args.out)

    with serial.Serial(args.port or ports[0], 115200, timeout=.04, write_timeout=1) as device:
        try:
            session['firmware_banner'] = handshake(device)
            save()
            with paths[1].open('x', newline='') as capture, paths[2].open('x') as log:
                fields = ['t_ms', 'joint', 'target_us', 'pulse_us', 'battery_mv']
                writer = csv.DictWriter(capture, fieldnames=fields, lineterminator='\n')
                writer.writeheader()
                latest = None
                received_at = 0
                settled_at = None
                announced = None
                keep_at = 0
                print(HELP, flush=True)
                print('Connected, PWM stopped. Awaiting an explicit lower/upper command.', flush=True)
                while True:
                    now = time.monotonic()
                    if now >= keep_at:
                        device.write(b'keep\n')
                        keep_at = now + 1
                    line = device.readline().decode('ascii', errors='replace').strip()
                    if line:
                        log.write(line + '\n')
                        log.flush()
                        row = parse_data(line)
                        if row is not None:
                            previous = latest
                            latest = row
                            received_at = time.monotonic()
                            writer.writerow(row)
                            capture.flush()
                            same = previous and all(previous[k] == row[k] for k in ['joint', 'target_us', 'pulse_us'])
                            if row['joint'] >= 0 and row['pulse_us'] == row['target_us']:
                                if settled_at is None or not same:
                                    settled_at = received_at
                                key = (row['joint'], row['pulse_us'])
                                if received_at - settled_at >= .2 and key != announced:
                                    announced = key
                                    print(f"SETTLED: {'lower' if row['joint'] == 0 else 'upper'} at {row['pulse_us']} us; BAT {row['battery_mv']} mV. Physical angle unmeasured.", flush=True)
                            else:
                                settled_at = None
                        else:
                            print(line, flush=True)
                            if line.startswith(('OFF', 'REFUSED', 'ERROR')):
                                latest = None
                                settled_at = None
                                announced = None
                    ready, _, _ = select.select([sys.stdin], [], [], 0)
                    if not ready:
                        continue
                    text = sys.stdin.readline()
                    if not text:
                        break
                    text = text.strip()
                    if text in ('quit', 'q', 'exit'):
                        break
                    if text == 'help':
                        print(HELP, flush=True)
                        continue
                    if text.startswith('mark '):
                        pieces = text.split(maxsplit=2)
                        try:
                            angle = float(pieces[1])
                            if not math.isfinite(angle) or abs(angle) > 180:
                                raise ValueError('Angle must be finite and within +/-180 degrees.')
                            if latest is None or latest['joint'] < 0 or settled_at is None or time.monotonic() - settled_at < .2 or time.monotonic() - received_at > .3:
                                raise ValueError('No fresh, settled active pulse to associate with this angle.')
                            point = dict(latest, joint_name='lower' if latest['joint'] == 0 else 'upper',
                                         visual_angle_deg=angle, note=pieces[2] if len(pieces) > 2 else '',
                                         recorded_utc=datetime.now(timezone.utc).isoformat())
                            session['observations'].append(point)
                            save()
                            print('SAVED: ' + json.dumps(point), flush=True)
                        except ValueError as error:
                            print('Not saved: ' + str(error), flush=True)
                        continue
                    if text in ('+', '-'):
                        if latest is None or latest['joint'] < 0 or time.monotonic() - received_at > .3:
                            print('Select a joint first; no fresh active telemetry.', flush=True)
                            continue
                        text = 'set ' + str(latest['target_us'] + (25 if text == '+' else -25))
                    elif text.startswith('pulse '):
                        text = 'set ' + text[6:]
                    if text not in ('lower', 'upper', 'off', 'status') and not text.startswith(('set ', 'window ')):
                        print('Unknown command; sending PWM stop.', flush=True)
                        text = 'off'
                    if len(text) > 45 or not text.isascii():
                        print('Invalid command; sending PWM stop.', flush=True)
                        text = 'off'
                    session['events'].append({'sent': text, 'at_utc': datetime.now(timezone.utc).isoformat()})
                    save()
                    device.write((text + '\n').encode('ascii'))
                    if text != 'status':
                        latest = None
                        settled_at = None
                        announced = None
        except KeyboardInterrupt:
            print('\nStopping PWM.', flush=True)
        finally:
            try:
                device.write(b'!\noff\n')
            finally:
                session['closed_utc'] = datetime.now(timezone.utc).isoformat()
                save()
    print(f'Session saved to {args.out}. PWM stop requested; battery power remains connected.', flush=True)


if __name__ == '__main__':
    main()
