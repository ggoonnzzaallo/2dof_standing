"""Exercise the exact portable retry supervisor: stall timing, varied bounded kicks."""
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
 RecoveryStrategy s;s.reset(19);float down[3]={1,0,0},target[2]={0,0},action[2]={0,0};
 std::set<int> patterns;unsigned previousRetries=0;int maximum=0;
 for(int frame=1;frame<5000;++frame){
   action[0]=action[1]=0;bool active=s.apply(down,target,action);
   if(frame<250)assert(!active);if(frame==250)assert(active&&s.retries==1);
   if(s.retries>previousRetries){patterns.insert(s.pattern);previousRetries=s.retries;}
   for(int i=0;i<2;++i){assert(std::isfinite(action[i])&&fabs(action[i])<=1);
     float next=fmaxf(-s.limit,fminf(s.limit,target[i]+s.increment*action[i]));
     assert(fabs(next-target[i])<=.100001f);target[i]=next;
     maximum=fmax(maximum,int(fabs(target[i])*1000));}
 }
 assert(patterns.size()==8&&maximum>1200&&maximum<=1397); // All 8 signs/orders and large sweep.
 down[0]=0;down[2]=-1;
 for(int f=0;f<1000;++f){action[0]=.2;action[1]=-.3;bool active=s.apply(down,target,action);assert(!active);assert(action[0]==.2f&&action[1]==-.3f);}
 assert(!s.active&&s.uprightTicks==50);
 // A base stuck 16 degrees from level must not be mistaken for a recovery.
 RecoveryStrategy near;near.reset(41);float lean[3]={.28f,0,-.96f};bool escaped=false;
 for(int f=0;f<300;++f){action[0]=action[1]=0;escaped|=near.apply(lean,target,action);}
 assert(escaped&&near.retries==1);
 s.reset(19);assert(s.tick==0&&s.retries==0&&!s.active);
}
''')
    subprocess.run(['c++','-std=c++11','-O2',str(p/'check.cpp'),'-o',str(p/'check')],check=True)
    subprocess.run([str(p/'check')],check=True)
print('PASS: 5 s stalled trigger, 8 bounded varied patterns, large sweeps, recovery cancellation and reset.')
