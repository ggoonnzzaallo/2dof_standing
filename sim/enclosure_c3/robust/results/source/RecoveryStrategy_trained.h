#pragma once
#include <math.h>
#include <stdint.h>

// Portable 50 Hz retry supervisor: same code runs in MuJoCo and on the XIAO.
// It changes bounded recovery patterns when the base stays fallen; never clears
// inactivity, sensor, battery or timing faults. No online weight updates.
struct RecoveryStrategy {
  uint32_t tick=0,fallenAt=0,progressAt=0,randomState=1;
  uint32_t retries=0;
  uint16_t age=0,duration=32;
  uint8_t uprightTicks=0,pattern=0;
  bool active=false;
  float best=-1,start[2]={},amplitude=1.3f;
  static constexpr float increment=.10f,limit=1.3962634016f;
  void reset(uint32_t seed=1){*this=RecoveryStrategy();randomState=seed?seed:1;}
  uint32_t random(){randomState=1664525u*randomState+1013904223u;return randomState;}
  bool apply(const float* down,const float* target,float* action){
    ++tick;const float up=-down[2];
    if(up>.94f){if(uprightTicks<15)++uprightTicks;}else uprightTicks=0;
    if(uprightTicks>=15){fallenAt=progressAt=tick;best=up;active=false;return false;}
    if(up>best+.12f){best=up;progressAt=tick;}
    // Stop a kick promptly as the base comes near level; policy finishes landing.
    if(active&&up>.90f){active=false;fallenAt=progressAt=tick;best=up;}
    if(!active&&up<.90f&&((tick-fallenAt>=250&&tick-progressAt>=100)||tick-fallenAt>=450)){
      active=true;age=0;pattern=uint8_t(retries++%8);
      duration=uint16_t(28+random()%13);amplitude=1.22f+.1762634f*float(random()%1001)/1000.f;
      start[0]=target[0];start[1]=target[1];
    }
    if(!active)return false;
    const int stage=age/duration;const float phase=float(age%duration+1)/duration;
    const float blend=.5f-.5f*cosf(3.14159265359f*phase);
    const float goals[4][2]={{-1.f,0.f},{1.f,-1.f},{0.f,1.f},{0.f,0.f}};
    float goal[2]={goals[stage][0]*amplitude,goals[stage][1]*amplitude};
    if(pattern&1){const float tmp=goal[0];goal[0]=goal[1];goal[1]=tmp;}
    if(pattern&2)goal[0]=-goal[0];if(pattern&4)goal[1]=-goal[1];
    for(int i=0;i<2;++i){const float desired=start[i]+blend*(goal[i]-start[i]);
      action[i]=fmaxf(-1.f,fminf(1.f,(desired-target[i])/increment));}
    ++age;
    if(age%duration==0){start[0]=goal[0];start[1]=goal[1];}
    if(age>=4*duration){active=false;fallenAt=progressAt=tick;best=up;}
    return true;
  }
};
