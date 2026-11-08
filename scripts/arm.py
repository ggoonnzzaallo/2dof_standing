"""Mac controls: arm, stop, latch no-PWM charging mode, or inspect state."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from control import handshake

ROOT = Path(__file__).resolve().parents[1]
MODES = {0: 'OFF', 1: 'NEUTRAL HOLD', 2: 'USB TRIAL', 3: 'SHADOW', 4: 'STANDALONE', 5: 'CHARGE / PWM OFF', 6: 'INACTIVE / REBOOT REQUIRED'}


def parse_state(line):
    fields = line.split(',', 6)
    if len(fields) != 7 or fields[0] != 'STATE':
        return None
    mode, battery, frames, ready, errors = map(int, fields[1:6])
    if mode not in MODES or not 0 <= battery <= 10000 or frames < 0 or ready not in (0, 1) or errors < 0:
        raise ValueError('Invalid device state: ' + line)
    return {'mode': mode, 'mode_name': MODES[mode], 'battery_mv': battery, 'policy_frames': frames,
            'sensor_ready': bool(ready), 'i2c_errors': errors, 'last_stop': fields[6]}


def stop_pwm(device, clock=time.monotonic):
    device.write(b'!\noff\n')
    deadline = clock() + 1
    while clock() < deadline:
        line = device.readline().decode('ascii', errors='replace').strip()
        if line.startswith('OFF'):
            return line
    raise RuntimeError('Stop not acknowledged. Unplug USB and isolate battery (Rev C: slide OFF).')


def query_state(device, clock=time.monotonic, running=False):
    deadline = clock() + 3
    next_request = 0
    while clock() < deadline:
        if clock() >= next_request:
            device.write(b'state\n')
            next_request = clock() + .2
        line = device.readline().decode('ascii', errors='replace').strip()
        state = parse_state(line)
        if state is not None:
            if not running or state['mode'] == 4 and state['policy_frames'] > 0:
                return state
            if state['mode'] != 4:
                raise RuntimeError('Standalone mode did not remain active: ' + line)
        if running and line.startswith(('OFF', 'REFUSED', 'ERROR')):
            raise RuntimeError(line)
    raise RuntimeError('Device state was not confirmed.')


def operate(device, action, clock=time.monotonic):
    result = {'action': action}
    if action == 'stop':
        result['stop_acknowledgement'] = stop_pwm(device, clock)
        result['device_state'] = query_state(device, clock)
        if result['device_state']['mode'] not in (0, 6):
            raise RuntimeError('Device did not remain stopped.')
        return result
    if action == 'status':
        result['device_state'] = query_state(device, clock)
        return result
    if action == 'charge':
        try:
            result['stop_acknowledgement'] = stop_pwm(device, clock)
            result['firmware_banner'] = handshake(device, require_ready=False)
            if query_state(device, clock)['mode'] not in (0, 6):
                raise RuntimeError('PWM stop was not confirmed before charge mode.')
            device.write(b'charge\n')
            deadline = clock() + 3
            while clock() < deadline:
                line = device.readline().decode('ascii', errors='replace').strip()
                if line.startswith('CHARGE:'):
                    result['charge_acknowledgement'] = line
                    break
                if line.startswith(('OFF', 'REFUSED', 'ERROR')):
                    raise RuntimeError(line + ' This harness requires controller firmware 0.8.')
            else:
                raise RuntimeError('Charge mode was not acknowledged; firmware 0.8 is required for this harness.')
            result['device_state'] = query_state(device, clock)
            if result['device_state']['mode'] != 5:
                raise RuntimeError('Device did not remain in no-PWM charge mode.')
            result['continues_after_serial_close'] = True
            result['net_charging_verified'] = False
            return result
        except BaseException:
            try:
                stop_pwm(device, clock)
            except (OSError, RuntimeError):
                pass
            raise
    handed_over = False
    try:
        result['firmware_banner'] = handshake(device)  # Explicitly disarms before new arming.
        device.reset_input_buffer()
        print('Setting both joints to neutral, then starting the policy...', flush=True)
        device.write(b'arm\n')
        deadline = clock() + 3
        next_keep = 0
        armed = False
        while clock() < deadline:
            if clock() >= next_keep:
                device.write(b'keep\n')
                next_keep = clock() + .25
            line = device.readline().decode('ascii', errors='replace').strip()
            if line.startswith('ARMED:'):
                armed = True
                break
            if line.startswith(('OFF', 'REFUSED', 'ERROR')):
                raise RuntimeError(line)
        if not armed:
            raise RuntimeError('Neutral arming was not acknowledged.')
        deadline = clock() + 1.2
        while clock() < deadline:
            if clock() >= next_keep:
                device.write(b'keep\n')
                next_keep = clock() + .25
            line = device.readline().decode('ascii', errors='replace').strip()
            if line.startswith(('OFF', 'REFUSED', 'ERROR')):
                raise RuntimeError(line)
        device.write(b'standalone\n')
        deadline = clock() + 3
        accepted = False
        while clock() < deadline:
            line = device.readline().decode('ascii', errors='replace').strip()
            if line.startswith('STANDALONE:'):
                accepted = True
                result['handoff_acknowledgement'] = line
                break
            if line.startswith(('OFF', 'REFUSED', 'ERROR')):
                raise RuntimeError(line)
        if not accepted:
            raise RuntimeError('Standalone handoff was not acknowledged.')
        result['device_state'] = query_state(device, clock, running=True)
        handed_over = True
        result['continues_after_serial_close'] = True
        return result
    finally:
        # Successful handoff must NOT send the supervisor's usual finally/off.
        if not handed_over:
            try:
                result['failure_stop_acknowledgement'] = stop_pwm(device, clock)
            except (OSError, RuntimeError):
                pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['arm', 'stop', 'charge', 'status'])
    parser.add_argument('--port')
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    import serial
    from serial.tools import list_ports
    ports = [p.device for p in list_ports.comports() if p.vid == 0x2886 and p.pid == 0x8045]
    if args.port and args.port not in ports:
        parser.error('--port must identify the classic XIAO Sense application.')
    if not args.port and len(ports) != 1:
        parser.error('Connect the XIAO by USB; specify --port if more than one is attached.')
    output = args.out or ROOT/'build/arming'/f'{args.action}_{time.time_ns()}.json'
    if output.exists():
        parser.error('Choose a new output filename.')
    output.parent.mkdir(parents=True, exist_ok=True)
    record = {'created_utc': datetime.now(timezone.utc).isoformat(), 'action': args.action}
    try:
        with serial.Serial(args.port or ports[0], 115200, timeout=.05, write_timeout=1) as device:
            record.update(operate(device, args.action))
        record['status'] = 'confirmed'
    except (OSError, RuntimeError, ValueError, KeyboardInterrupt) as error:
        record['status'] = 'failed'
        record['error'] = str(error) or 'Interrupted.'
    output.write_text(json.dumps(record, indent=2) + '\n')
    if record['status'] != 'confirmed':
        raise SystemExit('Not confirmed: ' + record['error'] + '\nRecord: ' + str(output))
    state = record['device_state']
    print(f"{state['mode_name']} | BAT {state['battery_mv']/1000:.3f} V | frames {state['policy_frames']}")
    if args.action == 'arm':
        print('Armed. Unplug USB: the robot will keep running on battery.')
        print('Firmware 0.5+: 60 s of base IMU inactivity stops PWM until reboot.')
        print('Stop via ./robot stop. Rev C full OFF: unplug USB and slide the master switch OFF.')
    elif args.action == 'stop':
        print('PWM stopped. Rev C full OFF: unplug USB and slide the master switch OFF.')
    elif args.action == 'charge':
        print('Charge mode latched; PWM is OFF. Servos still receive power.')
        if 'reboot required' in state['last_stop']:
            print('Inactivity lock remains set: reboot before arming again.')
        print('Rev C: keep the master switch ON and USB connected for charging.')
        print('This confirms PWM shutdown, not positive battery current or a full battery.')
        print('After charging: unplug USB and slide the master switch OFF for storage.')
    else:
        print('Last stop: ' + state['last_stop'])
        print('Status check did not request a stop.')
    print('Record: ' + str(output))


if __name__ == '__main__':
    main()
