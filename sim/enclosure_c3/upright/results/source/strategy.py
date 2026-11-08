"""Execute the exact firmware retry supervisor during simulation."""
from pathlib import Path
import ctypes,subprocess,tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
LIB=None;FOLDER=None
class Strategy:
    def __init__(self):
        global LIB,FOLDER
        if LIB is None:
            FOLDER=tempfile.TemporaryDirectory();p=Path(FOLDER.name)
            (p/'RecoveryStrategy.h').write_bytes((ROOT/'firmware/policy_control/RecoveryStrategy.h').read_bytes())
            (p/'strategy.cpp').write_text('''#include "RecoveryStrategy.h"
extern "C" {void* create(){return new RecoveryStrategy();}
void destroy(void* p){delete static_cast<RecoveryStrategy*>(p);}
void reset(void* p,unsigned seed){static_cast<RecoveryStrategy*>(p)->reset(seed);}
int apply(void* p,const float* down,const float* target,float* action,const float* gyro){return static_cast<RecoveryStrategy*>(p)->apply(down,target,action,gyro);}
void observe(void* p,const float* a,const float* w,float dt){static_cast<RecoveryStrategy*>(p)->observe(a,w,dt);}
unsigned retries(void* p){return static_cast<RecoveryStrategy*>(p)->retries;}}
''')
            subprocess.run(['c++','-std=c++11','-O2','-shared','-fPIC',str(p/'strategy.cpp'),'-o',str(p/'strategy.so')],check=True)
            LIB=ctypes.CDLL(str(p/'strategy.so'));ptr=ctypes.POINTER(ctypes.c_float)
            LIB.create.restype=ctypes.c_void_p;LIB.destroy.argtypes=[ctypes.c_void_p]
            LIB.reset.argtypes=[ctypes.c_void_p,ctypes.c_uint];LIB.apply.argtypes=[ctypes.c_void_p,ptr,ptr,ptr,ptr]
            LIB.observe.argtypes=[ctypes.c_void_p,ptr,ptr,ctypes.c_float]
            LIB.retries.argtypes=[ctypes.c_void_p];LIB.retries.restype=ctypes.c_uint
        self.lib=LIB;self.handle=LIB.create()
    def reset(self,seed):self.lib.reset(self.handle,int(seed or 1))
    def apply(self,down,target,action,gyro):
        ptr=ctypes.POINTER(ctypes.c_float)
        d=np.ascontiguousarray(down,dtype=np.float32);t=np.ascontiguousarray(target,dtype=np.float32);a=np.array(action,dtype=np.float32,copy=True)
        g=np.ascontiguousarray(gyro,dtype=np.float32)
        active=bool(self.lib.apply(self.handle,d.ctypes.data_as(ptr),t.ctypes.data_as(ptr),a.ctypes.data_as(ptr),g.ctypes.data_as(ptr)))
        return a,active
    def observe(self,accel,gyro,dt):
        p=ctypes.POINTER(ctypes.c_float);a=np.ascontiguousarray(accel,dtype=np.float32);g=np.ascontiguousarray(gyro,dtype=np.float32)
        self.lib.observe(self.handle,a.ctypes.data_as(p),g.ctypes.data_as(p),float(dt))
    @property
    def retries(self):return self.lib.retries(self.handle)
    def close(self):
        if self.handle:self.lib.destroy(self.handle);self.handle=None
