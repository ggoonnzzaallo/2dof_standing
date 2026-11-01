"""Export simulation-only actor and verify compiled C against its SB3 outputs."""
from pathlib import Path
import argparse
import ctypes
import hashlib
import json
import os
import subprocess
import sys
import tempfile
os.environ.setdefault('MPLCONFIGDIR','/tmp/2dof-mpl-cache')
import numpy as np
import torch
from stable_baselines3 import PPO

HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from export_actor import export


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('model',type=Path)
    parser.add_argument('--dataset',type=Path)
    parser.add_argument('--out',type=Path,default=HERE/'results/policy_simulation_only.h')
    args = parser.parse_args()
    torch.set_num_threads(1)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    count = export(args.model,args.out)
    model = PPO.load(args.model,device='cpu')
    observations = np.random.default_rng(19).uniform(-1,1,(1000,10)).astype(np.float32)
    if args.dataset:
        real = np.load(args.dataset)['observation']
        observations = np.vstack([observations,real[np.linspace(0,len(real)-1,1000,dtype=int)]])
    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        (folder/'policy.h').write_bytes(args.out.read_bytes())
        (folder/'test.c').write_text('#include "policy.h"\nvoid infer(const float *x,float *y){robot_policy(x,y);}\n')
        subprocess.run(['cc','-shared','-fPIC','-O2',str(folder/'test.c'),'-o',str(folder/'policy.so'),'-lm'],check=True)
        lib = ctypes.CDLL(str(folder/'policy.so'))
        pointer = ctypes.POINTER(ctypes.c_float)
        lib.infer.argtypes = [pointer,pointer];lib.infer.restype = None
        error = 0.
        for obs in observations:
            actual = np.zeros(2,dtype=np.float32)
            lib.infer(obs.ctypes.data_as(pointer),actual.ctypes.data_as(pointer))
            expected = model.predict(obs,deterministic=True)[0]
            error = max(error,float(np.max(np.abs(actual-expected))))
        assert error<1e-5,error
    result = {'status':'passed','model_sha256':hashlib.sha256(args.model.read_bytes()).hexdigest(),
              'actor_header_sha256':hashlib.sha256(args.out.read_bytes()).hexdigest(),
              'actor_parameters':count,'actor_weight_bytes_float32':count*4,
              'host_C_test_vectors':len(observations),'host_C_max_absolute_error':error,
              'MCU_timing_tested':False,'firmware_uploaded':False,'hardware_validation_complete':False,
              'note':'Mathematical host parity only. Calibrate sensor/servo mapping, limits and timing before hardware transfer.'}
    args.out.with_suffix('.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__':
    main()
