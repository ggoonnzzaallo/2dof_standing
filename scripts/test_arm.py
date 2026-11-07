"""Check handoff versus cleanup: successful arm must survive serial close."""
from collections import deque
import unittest
from arm import operate, parse_state


class Device:
    def __init__(self, refuse=False, ready=True, charge_supported=True, version='0.6', locked=False):
        self.time=0.;self.mode=0;self.frames=0;self.ready=ready;self.refuse=refuse
        self.lines=deque();self.commands=[];self.armed_at=0;self.closed=False;self.charge_supported=charge_supported
        self.version=version;self.locked=locked
    def now(self):return self.time
    def reset_input_buffer(self):self.lines.clear()
    def write(self,data):
        for command in data.decode().splitlines():
            self.commands.append(command)
            if command in ('!','off'):
                self.mode=6 if self.locked else 0;self.lines.append('OFF. PWM stopped.')
            elif command=='status':
                self.lines.extend([f'ROBOT POLICY CONTROL {self.version}',f'MODE: {self.mode}',f'INACTIVITY_LOCKED: {int(self.locked)}',f'IMU_READY: {int(self.ready)}',f'FILTER_READY: {int(self.ready)}','READY'])
            elif command=='arm':
                assert not self.locked
                self.mode=1;self.armed_at=self.time;self.lines.append('ARMED: nominal neutral.')
            elif command=='charge':
                if self.charge_supported:
                    self.mode=5;self.lines.append('CHARGE: PWM stopped and held LOW.')
                else:
                    self.mode=0;self.lines.append('OFF. Unknown command on old firmware.')
            elif command=='standalone':
                if self.refuse:
                    self.mode=0;self.lines.append('REFUSED: test rejection.')
                else:
                    assert self.time-self.armed_at>=1
                    self.mode=4;self.lines.append('STANDALONE: running; USB may be unplugged.')
            elif command=='state':
                self.lines.append(f'STATE,{self.mode},4100,{self.frames},{int(self.ready)},0,Test state.')
    def readline(self):
        self.time+=.05
        if self.mode==4:self.frames+=2
        return ((self.lines.popleft()+'\n').encode() if self.lines else b'')
    def close(self):self.closed=True


class ArmingTests(unittest.TestCase):
    def test_success_leaves_robot_running_after_close(self):
        device=Device()
        result=operate(device,'arm',device.now)
        device.close()
        self.assertEqual(result['device_state']['mode'],4)
        self.assertGreater(result['device_state']['policy_frames'],0)
        self.assertEqual(device.mode,4)
        tail=device.commands[device.commands.index('standalone')+1:]
        self.assertNotIn('off',tail);self.assertNotIn('!',tail)
        self.assertTrue(result['continues_after_serial_close'])
    def test_failed_handoff_requests_stop(self):
        device=Device(refuse=True)
        with self.assertRaisesRegex(RuntimeError,'test rejection'):
            operate(device,'arm',device.now)
        self.assertEqual(device.mode,0)
        self.assertIn('!',device.commands[device.commands.index('standalone')+1:])
    def test_status_never_requests_stop_or_rearm(self):
        device=Device();device.mode=4;device.frames=100
        result=operate(device,'status',device.now)
        self.assertEqual(result['device_state']['mode'],4)
        self.assertEqual(device.mode,4)
        self.assertEqual(device.commands,['state'])
    def test_stop_works_even_without_ready_filter(self):
        device=Device(ready=False);device.mode=4
        result=operate(device,'stop',device.now)
        self.assertEqual(result['device_state']['mode'],0)
        self.assertFalse(result['device_state']['sensor_ready'])
        self.assertNotIn('arm',device.commands)
    def test_state_parser_validates_protocol(self):
        self.assertIsNone(parse_state('D,irrelevant telemetry'))
        with self.assertRaises(ValueError):parse_state('STATE,99,4100,10,1,0,test')
    def test_charge_disarms_and_survives_close_without_sensor_readiness(self):
        device=Device(ready=False);device.mode=4;device.frames=100
        result=operate(device,'charge',device.now)
        device.close()
        self.assertEqual(result['device_state']['mode'],5)
        self.assertEqual(device.mode,5)
        self.assertNotIn('arm',device.commands)
        self.assertFalse(result['net_charging_verified'])
        tail=device.commands[device.commands.index('charge')+1:]
        self.assertNotIn('off',tail);self.assertNotIn('!',tail)
    def test_charge_on_old_firmware_fails_stopped(self):
        device=Device(charge_supported=False);device.mode=4
        with self.assertRaisesRegex(RuntimeError,'0.4'):
            operate(device,'charge',device.now)
        self.assertEqual(device.mode,0)
        self.assertNotIn('arm',device.commands)
    def test_old_pin_mapping_is_rejected_before_arm_or_charge(self):
        for version in ('0.2','0.3'):
            for action in ('arm','charge'):
                with self.subTest(version=version,action=action):
                    device=Device(version=version)
                    with self.assertRaisesRegex(RuntimeError,'D8 lower / D7 upper'):
                        operate(device,action,device.now)
                    self.assertNotIn('arm',device.commands)
                    self.assertNotIn('charge',device.commands)
                    self.assertEqual(device.mode,0)
    def test_inactivity_refuses_arm_before_any_motion_command(self):
        device=Device(locked=True)
        with self.assertRaisesRegex(RuntimeError,'inactivity lock'):
            operate(device,'arm',device.now)
        self.assertNotIn('arm',device.commands)
        self.assertEqual(device.mode,6)
    def test_inactivity_allows_stop_status_and_charge_without_clearing_lock(self):
        for action in ('stop','status','charge'):
            with self.subTest(action=action):
                device=Device(locked=True,ready=False);device.mode=6
                result=operate(device,action,device.now)
                self.assertEqual(result['device_state']['mode'],5 if action=='charge' else 6)
                self.assertTrue(device.locked)
                self.assertNotIn('arm',device.commands)
    def test_previous_d8_d7_firmware_remains_supported(self):
        for version in ('0.4','0.5'):
            device=Device(version=version)
            self.assertEqual(operate(device,'arm',device.now)['device_state']['mode'],4)
    def test_status_preserves_charge(self):
        device=Device();device.mode=5
        result=operate(device,'status',device.now)
        self.assertEqual(result['device_state']['mode'],5)
        self.assertEqual(device.commands,['state'])


if __name__=='__main__':unittest.main()
