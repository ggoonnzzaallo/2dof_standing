"""Open the enclosure-trained actor with matching physics and firmware IMU filter.

macOS: .venv-sim/bin/mjpython sim/enclosure/play.py
No serial port, upload or physical robot motion.
"""
from pathlib import Path
import os
import runpy
import sys
HERE=Path(__file__).resolve().parent
os.environ['ROBOT_MODEL_PATH']=str(HERE/'robot.xml')
script=HERE.parent/'recovery/play.py'
sys.path.insert(0,str(script.parent))
sys.argv=[str(script),'--model',str(HERE/'results/best.zip'),'--filtered',*sys.argv[1:]]
runpy.run_path(str(script),run_name='__main__')
