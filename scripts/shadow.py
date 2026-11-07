"""Record motor-disabled policy decisions and check MCU/host numerical parity.

Run with .tools/arduino/python/bin/python scripts/shadow.py --out build/shadow/initial.csv
"""
import argparse
import csv
import ctypes
import hashlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
LIMIT=1.3962634016

def handshake(device):
    banner=[];stopped=False;deadline=time.monotonic()+5;next_request=0
    while time.monotonic()<deadline:
        if time.monotonic()>=next_request:
            device.write(b'off\nstatus\n');next_request=time.monotonic()+.5
        line=device.readline().decode('ascii',errors='replace').strip()
        if line.startswith('OFF.'):stopped=True;banner=[]
        elif line.startswith('ROBOT ') and stopped:banner=[line]
        elif line and banner:banner.append(line)
        if 'Commands: status, sample, stream' in line and banner and 'FILTER_READY: 1' in banner:break
    if not ('ROBOT POLICY SHADOW 0.1' in banner and 'IMU_READY: 1' in banner and 'FILTER_READY: 1' in banner
            and any('MOTOR_OUTPUTS: DISABLED' in line for line in banner)):
        raise RuntimeError('Expected ready, motor-disabled shadow firmware.\n'+'\n'.join(banner))
    return banner

class HostActor:
    def __init__(self,header=None):
        self.folder=tempfile.TemporaryDirectory();folder=Path(self.folder.name)
        (folder/'policy.h').write_bytes(Path(header or ROOT/'sim/recovery/results/policy_simulation_only.h').read_bytes())
        (folder/'policy.c').write_text('#include "policy.h"\nvoid infer(const float *x,float *y){robot_policy(x,y);}\n')
        subprocess.run(['cc','-O2','-shared','-fPIC',str(folder/'policy.c'),'-o',str(folder/'policy.so'),'-lm'],check=True)
        self.lib=ctypes.CDLL(str(folder/'policy.so'))
        self.lib.infer.argtypes=[ctypes.POINTER(ctypes.c_float),ctypes.POINTER(ctypes.c_float)]
        self.lib.infer.restype=None
    def predict(self,obs):
        a=(ctypes.c_float*10)(*obs);b=(ctypes.c_float*2)();self.lib.infer(a,b);return list(b)
    def close(self):self.folder.cleanup()

def analyze(rows,actor):
    if len(rows)<20:raise ValueError('Need at least 20 shadow frames.')
    errors=[];history_error=0.;target_error=0.;norm_error=0.
    previous=[0.,0.];targets=[0.,0.]
    for row in rows:
        obs=[float(row[f'obs{i}']) for i in range(10)]
        action=[float(row[f'action{i}']) for i in range(2)]
        post=[float(row[f'virtual_target{i}_rad']) for i in range(2)]
        errors.append(max(abs(a-b) for a,b in zip(actor.predict(obs),action)))
        if max(map(abs,obs))>1.000001 or max(map(abs,action))>1.000001:raise ValueError('Observation/action out of bounds.')
        norm_error=max(norm_error,abs(math.sqrt(sum(float(row[k])**2 for k in ['down_x','down_y','down_z']))-1))
        for i in range(2):
            history_error=max(history_error,abs(obs[6+i]-targets[i]/LIMIT),abs(obs[8+i]-previous[i]))
            expected=max(-LIMIT,min(LIMIT,obs[6+i]*LIMIT+.06*action[i]))
            target_error=max(target_error,abs(expected-post[i]))
        previous=action;targets=post
    assert max(errors)<1e-4,errors
    assert history_error<1e-5 and target_error<1e-5 and norm_error<1e-4
    times=[int(r['t_us']) for r in rows];dt=[(b-a)%(2**32) for a,b in zip(times,times[1:])]
    inference=[int(r['inference_us']) for r in rows]
    tilt=[]
    for row in rows:
        cosine=max(-1.,min(1.,-float(row['down_z'])))
        tilt.append(math.degrees(math.acos(cosine)))
    return {'status':'passed','frames':len(rows),'actor_MCU_vs_host_max_absolute_error':max(errors),
            'virtual_history_max_error':history_error,'virtual_target_integration_max_error':target_error,
            'unit_DOWN_max_norm_error':norm_error,'inference_median_us':statistics.median(inference),
            'inference_max_us':max(inference),'telemetry_median_interval_us':statistics.median(dt),
            'maximum_reported_lateness_us':max(int(r['max_late_us']) for r in rows),
            'late_frames_over_10ms':max(int(r['late_frames']) for r in rows),
            'maximum_sample_age_us':max(int(r['sample_age_us']) for r in rows),
            'i2c_error_count_start':int(rows[0]['i2c_errors']),'i2c_error_count_end':int(rows[-1]['i2c_errors']),
            'saturated_frames':sum(int(r['saturated']) for r in rows),
            'tilt_min_deg':min(tilt),'tilt_max_deg':max(tilt),
            'physical_motor_commands_sent':False,
            'limitation':'Targets are virtual; no motor response or recovery is tested.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port');parser.add_argument('--seconds',type=float,default=10.)
    parser.add_argument('--out',type=Path,default=Path('build/shadow/initial.csv'))
    parser.add_argument('--label',default='orientation_unconfirmed')
    parser.add_argument('--analyze',type=Path)
    args=parser.parse_args()
    if not 1<=args.seconds<=25:parser.error('--seconds must be 1..25.')
    actor=HostActor()
    try:
        if args.analyze:
            with args.analyze.open(newline='') as f:print(json.dumps(analyze(list(csv.DictReader(f)),actor),indent=2))
            return
        import serial
        from serial.tools import list_ports
        ports=[p.device for p in list_ports.comports() if p.vid==0x2886 and p.pid==0x8045]
        if args.port and args.port not in ports:parser.error('--port must identify the XIAO Sense application.')
        if not args.port and len(ports)!=1:parser.error('Connect exactly one classic XIAO Sense or specify --port.')
        port=args.port or ports[0]
        if args.out.exists() or args.out.with_suffix('.json').exists():raise FileExistsError('Choose a new output filename.')
        args.out.parent.mkdir(parents=True,exist_ok=True)
        rows=[];header=None
        with serial.Serial(port,115200,timeout=.25,write_timeout=1) as device:
            try:
                banner=handshake(device);device.reset_input_buffer();device.write(b'stream\n')
                end=time.monotonic()+args.seconds
                with args.out.open('x',newline='') as f:
                    writer=None
                    while time.monotonic()<end:
                        line=device.readline().decode('ascii',errors='replace').strip()
                        if not line:continue
                        if line.startswith('t_us,down_x,'):
                            header=line.split(',');writer=csv.DictWriter(f,fieldnames=header,lineterminator='\n');writer.writeheader();continue
                        if line.startswith('ERROR:') or (writer and line.startswith('OFF.')):raise RuntimeError(line)
                        if not writer:continue
                        values=line.split(',')
                        if len(values)!=len(header) or not all(math.isfinite(float(v)) for v in values):raise ValueError(f'Invalid shadow row: {line}')
                        row=dict(zip(header,values));writer.writerow(row);rows.append(row)
            finally:
                device.write(b'!\noff\n')
        report=analyze(rows,actor)
        report.update({'label':args.label,'firmware_banner':banner,
                       'actor_header_sha256':hashlib.sha256((ROOT/'sim/recovery/results/policy_simulation_only.h').read_bytes()).hexdigest(),
                       'CSV_sha256':hashlib.sha256(args.out.read_bytes()).hexdigest()})
        args.out.with_suffix('.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    finally:actor.close()

if __name__=='__main__':main()
