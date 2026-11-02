"""Check handoff versus cleanup: successful arm must survive serial close."""
from collections import deque
import unittest
from arm import operate, parse_state


class Device:
    def __init__(self, refuse=False, ready=True):
        self.time=0.;self.mode=0;self.frames=0;self.ready=ready;self.refuse=refuse
        self.lines=deque();self.commands=[];self.armed_at=0;self.closed=False
    def now(self):return self.time
    def reset_input_buffer(self):self.lines.clear()
    def write(self,data):
        for command in data.decode().splitlines():
            self.commands.append(command)
            if command in ('!','off'):
                self.mode=0;self.lines.append('OFF. PWM stopped.')
            elif command=='status':
                self.lines.extend(['ROBOT POLICY CONTROL 0.2','MODE: 0','IMU_READY: 1','FILTER_READY: 1','READY'])
            elif command=='arm':
                self.mode=1;self.armed_at=self.time;self.lines.append('ARMED: nominal neutral.')
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


if __name__=='__main__':unittest.main()
