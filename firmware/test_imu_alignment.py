"""Check frame/sign conventions against a synthetic tilted sensor mount."""
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from imu_align import fit_rotation

angle = .37
expected = np.array([[np.cos(angle),0,np.sin(angle)], [0,1,0], [-np.sin(angle),0,np.cos(angle)]])
base_up = np.array([[0.,0.,1.],[-1.,0.,0.]])
sensor_up = base_up @ expected
actual, residual = fit_rotation(sensor_up,base_up)
assert np.allclose(actual,expected,atol=1e-7)
assert max(residual) < 1e-5
# Verify a third vector that was not part of fitting, plus gyro vector rotation.
assert np.allclose(actual @ (expected.T @ [0.,1.,0.]),[0.,1.,0.])
assert np.allclose(actual @ (expected.T @ [.4,-.2,.7]),[.4,-.2,.7])
try:
    fit_rotation([[0,0,1],[0,0,-1]],base_up)
    raise AssertionError('Collinear poses must be rejected')
except ValueError:
    pass
print('PASS: sensor-to-base rotation direction, handedness, held-out axis/gyro mapping and collinear-pose rejection.')
