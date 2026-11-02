"""Compile/load the exact portable firmware filter for offline simulation checks."""
from pathlib import Path
import ctypes
import subprocess
import tempfile
import numpy as np

ROOT=Path(__file__).resolve().parents[2]

class FilterRuntime:
    def __init__(self):
        self.folder=tempfile.TemporaryDirectory()
        folder=Path(self.folder.name)
        for name in ('GravityFilter.h','MountCalibration.h'):
            (folder/name).write_bytes((ROOT/'firmware/policy_shadow'/name).read_bytes())
        (folder/'filter.cpp').write_text('''
#include "GravityFilter.h"
#include "MountCalibration.h"
extern "C" {
void* create_filter(){return new GravityFilter();}
void destroy_filter(void* p){delete static_cast<GravityFilter*>(p);}
int feed(void* p,const float* accel,const float* gyro,float dt,int gyroClip,int accelClip,float* down,float* correctedGyro){
  float a[3];imuToBase(accel,a);gyroToBase(gyro,correctedGyro);
  auto* f=static_cast<GravityFilter*>(p);bool valid=f->update(a,correctedGyro,dt,gyroClip,accelClip);
  for(int i=0;i<3;++i)down[i]=f->down[i];return valid;
}
}
''')
        subprocess.run(['c++','-std=c++11','-O2','-shared','-fPIC',str(folder/'filter.cpp'),'-o',str(folder/'filter.so')],check=True)
        self.lib=ctypes.CDLL(str(folder/'filter.so'))
        pointer=ctypes.POINTER(ctypes.c_float)
        self.lib.create_filter.restype=ctypes.c_void_p
        self.lib.destroy_filter.argtypes=[ctypes.c_void_p]
        self.lib.feed.argtypes=[ctypes.c_void_p,pointer,pointer,ctypes.c_float,ctypes.c_int,ctypes.c_int,pointer,pointer]
        self.lib.feed.restype=ctypes.c_int
        self.handle=None
        self.reset()
    def reset(self):
        if self.handle:self.lib.destroy_filter(self.handle)
        self.handle=self.lib.create_filter();self.down=np.array([0,0,-1],dtype=np.float32)
        self.gyro=np.zeros(3,dtype=np.float32);self.ready=False
    def update(self,accel,gyro,dt,gyro_clip=False,accel_clip=False):
        a=np.ascontiguousarray(accel,dtype=np.float32);w=np.ascontiguousarray(gyro,dtype=np.float32)
        pointer=ctypes.POINTER(ctypes.c_float)
        self.ready=bool(self.lib.feed(self.handle,a.ctypes.data_as(pointer),w.ctypes.data_as(pointer),dt,gyro_clip,accel_clip,
                                      self.down.ctypes.data_as(pointer),self.gyro.ctypes.data_as(pointer)))
        return self.ready
    def close(self):
        if self.handle:self.lib.destroy_filter(self.handle);self.handle=None
        self.folder.cleanup()
