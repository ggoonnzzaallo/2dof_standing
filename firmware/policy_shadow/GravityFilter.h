#pragma once
#include <math.h>

// Body-frame unit DOWN estimator. Gyro propagation on SO(3), acceleration
// correction on the unit sphere. No yaw estimate or online bias adaptation.
class GravityFilter {
 public:
  float down[3] = {0,0,-1};
  bool ready = false;
  float accelTrust = 0;
  explicit GravityFilter(float gain=1.5f) : correctionGain(gain) {}

  bool update(const float accelG[3], const float gyroRadS[3], float dt, bool gyroSaturated=false, bool accelSaturated=false) {
    for (int i=0;i<3;++i) if (!isfinite(accelG[i]) || !isfinite(gyroRadS[i])) return invalidate();
    if (gyroSaturated || !isfinite(dt) || dt<0 || dt>.05f) return invalidate();
    const float norm = length(accelG);
    const float speed = length(gyroRadS);
    accelTrust = fmaxf(0.f,1.f-fabsf(norm-1.f)/.15f)/(1.f+.25f*speed*speed);
    if(accelSaturated)accelTrust=0;
    float measured[3] = {};
    if (norm>1e-6f) for (int i=0;i<3;++i) measured[i] = -accelG[i]/norm;
    if (!ready) {
      if (accelTrust<=0 || speed>.15f) {initialSamples=0;for(int i=0;i<3;++i)initialSum[i]=0;return false;}
      const float accumulatedNorm=length(initialSum);
      if(initialSamples && dot(initialSum,measured)<.995f*accumulatedNorm){
        initialSamples=0;for(int i=0;i<3;++i)initialSum[i]=0;
      }
      for(int i=0;i<3;++i)initialSum[i]+=measured[i];
      if(++initialSamples<20)return false;
      const float initialNorm=length(initialSum);
      if(initialNorm<.5f)return invalidate();
      for (int i=0;i<3;++i) down[i]=initialSum[i]/initialNorm;
      ready=true;
      return true;
    }
    if (dt<=0) return invalidate();
    if (speed>1e-8f) {
      float axis[3];
      for (int i=0;i<3;++i) axis[i]=-gyroRadS[i]/speed;
      rotate(down,axis,speed*dt); // dg/dt = -omega x g in rotating body coordinates.
    }
    if (accelTrust>0) {
      float axis[3]; cross(down,measured,axis);
      float sine=length(axis);
      const float cosine=fmaxf(-1.f,fminf(1.f,dot(down,measured)));
      const float error=atan2f(sine,cosine);
      if (sine<1e-7f && cosine<0) {
        // Deterministic perpendicular axis also permits a 180-degree correction.
        float ref[3]={}; int least=0;
        for(int i=1;i<3;++i) if(fabsf(down[i])<fabsf(down[least])) least=i;
        ref[least]=1;cross(down,ref,axis);sine=length(axis);
      }
      if(sine>1e-8f) {
        for(int i=0;i<3;++i)axis[i]/=sine;
        rotate(down,axis,error*(1.f-expf(-correctionGain*accelTrust*dt)));
      }
    }
    const float n=length(down);
    if(!isfinite(n)||n<.5f)return invalidate();
    for(int i=0;i<3;++i)down[i]/=n;
    return true;
  }

 private:
  float correctionGain;
  unsigned initialSamples=0;
  float initialSum[3]={};
  bool invalidate(){ready=false;accelTrust=0;initialSamples=0;for(int i=0;i<3;++i)initialSum[i]=0;return false;}
  static float dot(const float a[3],const float b[3]){return a[0]*b[0]+a[1]*b[1]+a[2]*b[2];}
  static float length(const float a[3]){return sqrtf(dot(a,a));}
  static void cross(const float a[3],const float b[3],float c[3]){
    c[0]=a[1]*b[2]-a[2]*b[1];c[1]=a[2]*b[0]-a[0]*b[2];c[2]=a[0]*b[1]-a[1]*b[0];
  }
  static void rotate(float v[3],const float axis[3],float angle){
    float c[3];cross(axis,v,c);const float d=dot(axis,v),s=sinf(angle),co=cosf(angle);
    for(int i=0;i<3;++i)v[i]=v[i]*co+c[i]*s+axis[i]*d*(1.f-co);
  }
};
