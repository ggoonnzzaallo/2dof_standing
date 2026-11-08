"""Preserve physical target interpretation when expanding 80-degree normalization."""
from pathlib import Path
import argparse
import torch
from stable_baselines3 import PPO
p=argparse.ArgumentParser(description=__doc__);p.add_argument('source',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
model=PPO.load(a.source,device='cpu')
with torch.no_grad():model.policy.mlp_extractor.policy_net[0].weight[:,6:8]*=90/80
model.save(a.out)
