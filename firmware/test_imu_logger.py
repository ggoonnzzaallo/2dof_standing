"""Check telemetry units/quality summaries without serial or hardware access."""
import importlib.util
from pathlib import Path
from collections import deque

path = Path(__file__).resolve().parents[1]/'scripts/imu.py'
spec = importlib.util.spec_from_file_location('imu_logger',path)
logger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(logger)

def rows():
    result = []
    for i in range(100):
        values = [(2**32-100000+i*20000) % 2**32,0,0,1,0,0,0,1,3900,i*4,0,0,1000]
        result.append(dict(zip(logger.FIELDS,map(str,values))))
    return result

data = rows()
report = logger.summarize(data)
assert report['rough_stationary_check'] and report['sensor_quality_check']
assert report['static_DOWN_sensor_estimate'] == [0,0,-1]
assert report['median_sample_interval_s'] == .02
assert report['duplicate_sample_rows'] == 0
for row in data:
    row['gx_rad_s'] = '.3'
assert not logger.summarize(data)['rough_stationary_check']
assert logger.summarize(data)['static_DOWN_sensor_estimate'] is None
data = rows();data[-1]['i2c_errors'] = '1'
assert not logger.summarize(data)['sensor_quality_check']
data = rows();data[10]['saturated'] = '1'
assert not logger.summarize(data)['sensor_quality_check']
data = rows();data[10]['t_us'] = data[9]['t_us']
assert logger.summarize(data)['duplicate_sample_rows'] == 1
assert not logger.summarize(data)['sensor_quality_check']
try:
    logger.summarize(rows()[:2])
    raise AssertionError('Too-short recordings must fail')
except ValueError:
    pass
class FakeSerial:
    def __init__(self, ready=True):
        self.ready = ready
        self.lines = deque([b'harging.\n', b'Commands: status, sample, stream\n'])
        self.writes = []
    def write(self, command):
        self.writes.append(command)
        self.lines.extend([b'OFF. Sensor stream stopped.\n', b'ROBOT IMU BENCH 0.4\n',
                           b'IMU_READY: 1\n' if self.ready else b'IMU_READY: 0\n',
                           b'Commands: status, sample, stream\n'])
    def readline(self):
        return self.lines.popleft() if self.lines else b''

serial = FakeSerial()
assert 'IMU_READY: 1' in logger.wait_ready(serial)
assert all(command == b'off\nstatus\n' for command in serial.writes)
try:
    logger.wait_ready(FakeSerial(ready=False))
    raise AssertionError('An unready sensor must fail the handshake')
except RuntimeError:
    pass
print('PASS: stationary DOWN sign, gyro-motion rejection, timestamp rollover, I2C/saturation/dropout quality and minimum sample count.')
print('PASS: partial USB startup banners are ignored; full ready status is required after stop acknowledgement.')
