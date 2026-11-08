"""Current heavy-C3 simulation, faster targets and exact firmware varied retries."""
from pathlib import Path
import sys
from robust_env import RobustEnv,HERE
import play as original_play

if __name__=='__main__':
    # The recovery directory precedes this script after robust_env loads it.
    # Use its viewer with our environment; observations/actions remain identical.
    original_play.FilteredEnv=RobustEnv
    if '--model' not in sys.argv:sys.argv.extend(['--model',str(HERE/'results/best.zip')])
    if '--filtered' not in sys.argv:sys.argv.append('--filtered')
    original_play.main()
