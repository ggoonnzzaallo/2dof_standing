"""Export the exact deterministic SB3 MLP mean and action clipping to portable C.
No VecNormalize: observation scaling lives in environment.py and must match firmware.
"""
from pathlib import Path
import argparse
import numpy as np
import torch
from stable_baselines3 import PPO

def export(model_path,out):
    m=PPO.load(model_path,device='cpu')
    layers=list(m.policy.mlp_extractor.policy_net)+[m.policy.action_net]
    assert len(layers)==5 and isinstance(layers[1],torch.nn.Tanh) and isinstance(layers[3],torch.nn.Tanh)
    linear=[layers[i] for i in (0,2,4)]
    assert [(l.in_features,l.out_features) for l in linear]==[(10,64),(64,64),(64,2)]
    chunks=['#pragma once\n#include <math.h>\n/* 10 inputs; fixed scaling documented in sim/README.md. */\n']
    count=0
    for i,l in enumerate(linear):
        for name,a in [('w',l.weight.detach().numpy()),('b',l.bias.detach().numpy())]:
            count+=a.size
            values=','.join(f'{float(x):.9e}f' for x in a.ravel())
            chunks.append(f'static const float {name}{i}[{a.size}]={{{values}}};\n')
    chunks.append('''static inline void robot_policy(const float obs[10], float action[2]) {
  float h1[64], h2[64];
  for(int i=0;i<64;i++){float s=b0[i]; for(int j=0;j<10;j++)s+=w0[i*10+j]*obs[j]; h1[i]=tanhf(s);}
  for(int i=0;i<64;i++){float s=b1[i]; for(int j=0;j<64;j++)s+=w1[i*64+j]*h1[j]; h2[i]=tanhf(s);}
  for(int i=0;i<2;i++){float s=b2[i]; for(int j=0;j<64;j++)s+=w2[i*64+j]*h2[j]; action[i]=fminf(1.f,fmaxf(-1.f,s));}
}
''')
    Path(out).write_text(''.join(chunks)); return count

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('model'); p.add_argument('output'); a=p.parse_args()
    print(f'{export(a.model,a.output)} float32 parameters exported (actor only).')
