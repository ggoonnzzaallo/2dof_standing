"""Analytic tests of the actual portable gravity-filter header; no hardware."""
from pathlib import Path
import subprocess
import tempfile

HEADER=Path(__file__).resolve().parent/'policy_shadow/GravityFilter.h'
TEST=r'''
#include "GravityFilter.h"
#include <cassert>
#include <limits>
#include <iostream>
float error(const float a[3],const float b[3]){
 float v=0;for(int i=0;i<3;++i)v+=(a[i]-b[i])*(a[i]-b[i]);return sqrtf(v);
}
void initialize(GravityFilter &f,const float a[3],const float w[3]){
 for(int i=0;i<20;++i)f.update(a,w,i?.005f:0.f);assert(f.ready);
}
int main(){
 float a[3]={0,0,1},w[3]={0,0,0},g[3]={0,0,-1};
 GravityFilter filter;initialize(filter,a,w);assert(error(filter.down,g)<1e-6);
 // Repeated complete rolls, including inverted, with analytic body-frame gravity.
 w[0]=3.14159265358979323846f;
 float worst=0;
 for(int i=1;i<=2000;++i){
  float angle=i*.005f*w[0];g[0]=0;g[1]=-sinf(angle);g[2]=-cosf(angle);
  for(int j=0;j<3;++j)a[j]=-g[j];
  assert(filter.update(a,w,.005f));worst=fmaxf(worst,error(filter.down,g));
 }
 assert(worst<1e-4f);
 // Gross translation must not pull the gravity estimate toward raw acceleration.
 GravityFilter pulse;float zero[3]={},upright[3]={0,0,1};initialize(pulse,upright,zero);
 float translated[3]={3,0,1};for(int i=0;i<100;++i)pulse.update(translated,zero,.005f);
 float down[3]={0,0,-1};assert(error(pulse.down,down)<1e-6&&pulse.accelTrust==0);
 assert(pulse.update(translated,zero,.005f,false,true)&&pulse.ready); // Gyro survives acceleration clipping.
 // Large gravity disagreement can recover even at the antipodal configuration.
 float inverted[3]={0,0,-1};for(int i=0;i<1600;++i)assert(pulse.update(inverted,zero,.005f));
 float up[3]={0,0,1};assert(error(pulse.down,up)<1e-4f);
 assert(!pulse.update(inverted,zero,.2f)&&!pulse.ready);
 initialize(pulse,inverted,zero);assert(error(pulse.down,up)<1e-6);
 assert(!pulse.update(inverted,zero,.005f,true));
 inverted[0]=std::numeric_limits<float>::quiet_NaN();assert(!pulse.update(inverted,zero,.005f));
 std::cout<<"PASS: static signs, ten full roll seconds, unit gravity, acceleration rejection, antipodal correction, gap/saturation/NaN invalidation. Worst analytic vector error: "<<worst<<"\n";
}
'''
with tempfile.TemporaryDirectory() as temp:
    p=Path(temp);(p/'GravityFilter.h').write_bytes(HEADER.read_bytes());(p/'test.cpp').write_text(TEST)
    subprocess.run(['c++','-std=c++11','-O2',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
