"""Exact runtime regression: full-range varied retries and level-base straight hold."""
from pathlib import Path
import subprocess,tempfile
HERE=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as d:
 p=Path(d);(p/'RecoveryStrategy.h').write_bytes((HERE/'policy_control/RecoveryStrategy.h').read_bytes())
 (p/'check.cpp').write_text(r'''
#include "RecoveryStrategy.h"
#include <cassert>
#include <cmath>
#include <set>
int main(){
 RecoveryStrategy s;s.reset(19);float down[3]={1,0,0},target[2]={0,0},action[2]={0,0},gyro[3]={0,0,0};
 std::set<int> patterns;unsigned previousRetries=0;float maximum=0;
 for(int frame=1;frame<5000;++frame){
   action[0]=action[1]=0;bool active=s.apply(down,target,action,gyro);
   if(frame<250)assert(!active);if(frame==250)assert(active&&s.retries==1);
   if(s.retries>previousRetries){patterns.insert(s.pattern);previousRetries=s.retries;}
   for(int i=0;i<2;++i){assert(std::isfinite(action[i])&&fabs(action[i])<=1);
     float next=fmaxf(-s.limit,fminf(s.limit,target[i]+s.increment*action[i]));
     assert(fabs(next-target[i])<=.100001f);target[i]=next;maximum=fmaxf(maximum,fabs(target[i]));}
 }
 assert(patterns.size()==8&&maximum>1.396f&&maximum<=1.570797f);
 s.reset(31);down[0]=0;down[2]=-1;target[0]=1.2;target[1]=-.8;
 for(int f=0;f<500;++f){
   action[0]=.8;action[1]=-.9;s.apply(down,target,action,gyro);
   if(f>=9){assert(s.neutralHold);assert(fabs(action[0])<=.400001&&fabs(action[1])<=.400001);}
   for(int i=0;i<2;++i)target[i]=fmaxf(-s.limit,fminf(s.limit,target[i]+s.increment*action[i]));
 }
 assert(s.neutralHold&&!s.active&&fabs(target[0])<1e-6&&fabs(target[1])<1e-6);
 // Hysteresis: small level noise keeps it straight; tilt or fast rotation exits.
 down[2]=-.985;s.apply(down,target,action,gyro);assert(s.neutralHold);
 down[2]=-.96;s.apply(down,target,action,gyro);assert(!s.neutralHold);
 down[2]=-1;for(int i=0;i<12;++i)s.apply(down,target,action,gyro);assert(s.neutralHold);
 gyro[0]=1.3;s.apply(down,target,action,gyro);assert(!s.neutralHold);gyro[0]=0;
 RecoveryStrategy near;near.reset(41);float lean[3]={.28f,0,-.96f};bool escaped=false;
 for(int f=0;f<300;++f){action[0]=action[1]=0;escaped|=near.apply(lean,target,action,gyro);}
 assert(escaped&&near.retries==1);
 // Table vibration must not prevent leveling when the gyro gravity estimate
 // has drifted. Feed the same raw IMU path used by the board and simulator.
 RecoveryStrategy vibrate;vibrate.reset(7);float biased[3]={.3f,0,-.954f},w[3]={.02f,0,0};
 float neutral[2]={.7f,-.4f};
 for(int f=0;f<1000;++f){
   float a[3]={f%2?.15f:-.15f,f%2?.2f:-.2f,f%2?1.9f:.1f};
   vibrate.observe(a,w,.005f);
   if(f%4==0){action[0]=.5;action[1]=-.7;vibrate.apply(biased,neutral,action,w);for(int i=0;i<2;++i)neutral[i]+=.1f*action[i];}
 }
 assert(vibrate.neutralHold&&fabs(neutral[0])<1e-6&&fabs(neutral[1])<1e-6);
 s.reset(19);assert(s.tick==0&&s.retries==0&&!s.active&&!s.neutralHold);
}
''')
 subprocess.run(['c++','-std=c++11','-O2',str(p/'check.cpp'),'-o',str(p/'check')],check=True)
 subprocess.run([str(p/'check')],check=True)
print('PASS: 90-degree varied patterns, neutral acquisition/hold, bounded 2 rad/s straightening, hysteresis, tilt/spin exit, stalled retry and reset.')
