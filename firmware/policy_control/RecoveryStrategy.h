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
  uint8_t uprightTicks=0,pattern=0,flatTicks=0;
  bool active=false,neutralHold=false;
  float best=-1,start[2]={},amplitude=1.3f,accelMean[3]={},gyroMean[3]={};
  uint16_t sensorSamples=0;
  static constexpr float increment=.10f,limit=1.5707963267948966f;
  void reset(uint32_t seed=1){*this=RecoveryStrategy();randomState=seed?seed:1;}
  uint32_t random(){randomState=1664525u*randomState+1013904223u;return randomState;}
  void observe(const float* accel,const float* gyro,float dt){
    if(!isfinite(dt)||dt<0||dt>.05f)return;
    for(int i=0;i<3;++i)if(!isfinite(accel[i])||!isfinite(gyro[i]))return;
    const float a=1.f-expf(-dt/.25f),b=1.f-expf(-dt/.08f);
    for(int i=0;i<3;++i){
      if(!sensorSamples){accelMean[i]=accel[i];gyroMean[i]=gyro[i];}
      else{accelMean[i]+=a*(accel[i]-accelMean[i]);gyroMean[i]+=b*(gyro[i]-gyroMean[i]);}
    }
    if(sensorSamples<65535)++sensorSamples;
  }
  bool apply(const float* down,const float* target,float* action,const float* gyro=nullptr){
    ++tick;const float up=-down[2];
    const float rawSpeed2=gyro?gyro[0]*gyro[0]+gyro[1]*gyro[1]+gyro[2]*gyro[2]:0.f;
    const float speed2=sensorSamples>=40?gyroMean[0]*gyroMean[0]+gyroMean[1]*gyroMean[1]+gyroMean[2]*gyroMean[2]:rawSpeed2;
    const float norm2=accelMean[0]*accelMean[0]+accelMean[1]*accelMean[1]+accelMean[2]*accelMean[2];
    // Low-pass the existing accelerometer samples to reject table/contact
    // vibration. At rest this also corrects a biased dynamic gravity estimate.
    const float levelUp=sensorSamples>=40&&norm2>.7225f&&norm2<1.3225f?accelMean[2]/sqrtf(norm2):up;
    // Hysteresis prevents the learned recovery actor from leaving a bent arm on
    // a level base. These are commanded joint references, not shaft readback.
    if(levelUp>.99026807f&&speed2<.36f){if(flatTicks<10)++flatTicks;}else flatTicks=0;
    if(neutralHold&&(levelUp<.97814760f||speed2>1.44f||rawSpeed2>4.f)){neutralHold=false;flatTicks=0;}
    if(flatTicks>=10)neutralHold=true;
    if(neutralHold){
      active=false;fallenAt=progressAt=tick;best=up;
      for(int i=0;i<2;++i)action[i]=fmaxf(-.4f,fminf(.4f,-target[i]/increment));
      return true; // Ease to neutral at at most 2 rad/s, then hold exactly zero.
    }
    if(up>.98480775f){if(uprightTicks<50)++uprightTicks;}else uprightTicks=0;
    if(uprightTicks>=50){fallenAt=progressAt=tick;best=up;active=false;return false;}
    if(up>best+.12f){best=up;progressAt=tick;}
    // Stop a kick promptly as the base comes near level; policy finishes landing.
    if(active&&up>.98480775f){active=false;fallenAt=progressAt=tick;best=up;}
    if(!active&&up<.98f&&((tick-fallenAt>=250&&tick-progressAt>=100)||tick-fallenAt>=450)){
      active=true;age=0;pattern=uint8_t(retries++%8);
      duration=uint16_t(30+random()%13);amplitude=1.3962634f+.174532925f*float(random()%1001)/1000.f;
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
