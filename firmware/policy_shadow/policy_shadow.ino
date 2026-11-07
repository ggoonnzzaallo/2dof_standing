// Read the calibrated IMU and log neural actions. NO PWM / servo code exists here.
#include <Arduino.h>
#include <Adafruit_TinyUSB.h>
#include <string.h>
#include "../imu_bench/Lsm6ds3.h"
#include "GravityFilter.h"
#include "MicrosecondClock.h"
#include "MountCalibration.h"
#include "../../sim/recovery/results/policy_simulation_only.h"

#ifndef TARGET_SEEED_XIAO_NRF52840_SENSE
#error "Use the classic XIAO nRF52840 Sense / non-mbed Seeed nRF52 core."
#endif

Lsm6ds3 imu;
MicrosecondClock clockUs;
GravityFilter attitude;
float accelBase[3]={},gyroBase[3]={},observation[10]={},action[2]={},virtualTarget[2]={},previousAction[2]={};
uint32_t sampleAt=0,lastPoll=0,nextPolicy=0,streamAt=0,batteryAt=0,inferenceUs=0,maxInferenceUs=0,lateUs=0,maxLateUs=0;
uint32_t policyFrames=0,lateFrames=0,filterRejects=0;
uint16_t batteryMv=0;
bool streaming=false,banner=false,discard=false;
char command[24];size_t used=0;
constexpr float JOINT_LIMIT_RAD=1.3962634016f;
const char *HEADER="t_us,down_x,down_y,down_z,gyro_x_rad_s,gyro_y_rad_s,gyro_z_rad_s,acc_norm_g,acc_trust,obs0,obs1,obs2,obs3,obs4,obs5,obs6,obs7,obs8,obs9,action0,action1,virtual_target0_rad,virtual_target1_rad,inference_us,max_inference_us,late_us,max_late_us,late_frames,filter_rejects,sample_age_us,sample_seq,i2c_errors,saturated,battery_mv";

uint16_t readBatteryMv(){
  analogReference(AR_INTERNAL_3_0);analogReadResolution(12);analogSampleTime(40);
  (void)analogRead(PIN_VBAT);uint32_t sum=0;for(int i=0;i<8;++i)sum+=analogRead(PIN_VBAT);
  return uint16_t((uint64_t(sum)*3000*1510)/(8ULL*4096*510));
}
float clip(float v){return fminf(1.f,fmaxf(-1.f,v));}
void resetPolicy(){
  for(int i=0;i<2;++i){virtualTarget[i]=0;previousAction[i]=0;action[i]=0;}
  policyFrames=lateFrames=0;inferenceUs=maxInferenceUs=lateUs=maxLateUs=0;
}
void stop(){streaming=false;resetPolicy();}
bool fresh(){return imu.ready&&attitude.ready&&sampleAt&&uint32_t(clockUs.now()-sampleAt)<20000;}
void status(){
  Serial.println("ROBOT POLICY SHADOW 0.1");
  Serial.println("MOTOR_OUTPUTS: DISABLED; D8/D7 LOW. Policy targets are virtual, not servo positions.");
  Serial.print("IMU_READY: ");Serial.println(imu.ready?1:0);
  Serial.print("FILTER_READY: ");Serial.println(attitude.ready?1:0);
  Serial.print("I2C_ERRORS: ");Serial.println(imu.errors);
  Serial.println("CALIBRATION: provisional static mounting rotation and recorded gyro bias; dynamic validation pending.");
  Serial.println("CLOCK: TIMER4 1 MHz; no DWT or core micros changes.");
  Serial.println("Commands: status, sample, stream (50 Hz, max 30 s), off, !, help");
}
void infer(){
  for(int i=0;i<3;++i){observation[i]=clip(attitude.down[i]);observation[i+3]=clip(gyroBase[i]/10.f);}
  for(int i=0;i<2;++i){observation[i+6]=clip(virtualTarget[i]/JOINT_LIMIT_RAD);observation[i+8]=previousAction[i];}
  const uint32_t at=clockUs.now();robot_policy(observation,action);inferenceUs=clockUs.now()-at;
  if(inferenceUs>maxInferenceUs)maxInferenceUs=inferenceUs;
  for(int i=0;i<2;++i){
    action[i]=clip(action[i]);
    virtualTarget[i]=fminf(JOINT_LIMIT_RAD,fmaxf(-JOINT_LIMIT_RAD,virtualTarget[i]+.06f*action[i]));
    previousAction[i]=action[i];
  }
  ++policyFrames;
}
void field(float value){Serial.print(',');Serial.print(value,7);}
void integer(uint32_t value){Serial.print(',');Serial.print(value);}
void report(){
  Serial.print(sampleAt);
  for(int i=0;i<3;++i)field(attitude.down[i]);for(int i=0;i<3;++i)field(gyroBase[i]);
  field(sqrtf(accelBase[0]*accelBase[0]+accelBase[1]*accelBase[1]+accelBase[2]*accelBase[2]));field(attitude.accelTrust);
  for(int i=0;i<10;++i)field(observation[i]);for(int i=0;i<2;++i)field(action[i]);
  for(int i=0;i<2;++i)field(virtualTarget[i]);
  integer(inferenceUs);integer(maxInferenceUs);integer(lateUs);integer(maxLateUs);integer(lateFrames);integer(filterRejects);
  integer(clockUs.now()-sampleAt);integer(imu.sequence);integer(imu.errors);integer(imu.sample.saturated?1:0);integer(batteryMv);
  Serial.println();
}
void handleCommand(){
  command[used]=0;stop();
  if(!strcmp(command,"stream")||!strcmp(command,"sample")){
    if(!fresh()){Serial.println("ERROR: IMU/filter unavailable or stale.");return;}
    Serial.println(HEADER);
    if(!strcmp(command,"sample")){infer();report();resetPolicy();}
    else{streaming=true;streamAt=millis();nextPolicy=clockUs.now()+20000;}
  }else if(!strcmp(command,"off"))Serial.println("OFF. Shadow stopped; motor outputs disabled.");
  else status();
}
void setup(){
  digitalWrite(D8,LOW);pinMode(D8,OUTPUT);digitalWrite(D7,LOW);pinMode(D7,OUTPUT);pinMode(D2,INPUT);
  digitalWrite(PIN_CHARGING_CURRENT,LOW);pinMode(PIN_CHARGING_CURRENT,OUTPUT);
  digitalWrite(VBAT_ENABLE,LOW);pinMode(VBAT_ENABLE,OUTPUT);
  Serial.begin(115200);clockUs.begin();imu.begin();batteryMv=readBatteryMv();
}
void loop(){
  uint32_t now=clockUs.now();
  if(uint32_t(now-lastPoll)>=750){
    lastPoll=now;
    if(imu.poll()){
      const uint32_t stamp=clockUs.now();const float dt=sampleAt?float(uint32_t(stamp-sampleAt))*1e-6f:0.f;
      sampleAt=stamp;imuToBase(imu.sample.accelG,accelBase);gyroToBase(imu.sample.gyroRadS,gyroBase);
      bool gyroClip=false,accelClip=false;
      for(int i=0;i<3;++i){
        gyroClip |= fabsf(imu.sample.gyroRadS[i])>=39.95f;
        accelClip |= fabsf(imu.sample.accelG[i])>=7.9788f;
      }
      if(!attitude.update(accelBase,gyroBase,dt,gyroClip,accelClip))++filterRejects;
    }
  }
  if(uint32_t(millis()-batteryAt)>=200){batteryAt=millis();batteryMv=readBatteryMv();}
  if(!Serial){stop();banner=false;used=0;discard=false;delay(1);return;}
  if(!banner){status();banner=true;}
  while(Serial.available()){
    const char c=Serial.read();
    if(c=='!'){stop();used=0;discard=true;Serial.println("OFF. Shadow stopped.");}
    else if(c=='\n'||c=='\r'){if(!discard&&used)handleCommand();used=0;discard=false;}
    else if(!discard&&used<sizeof(command)-1)command[used++]=c;
    else{stop();used=0;discard=true;}
  }
  if(streaming){
    now=clockUs.now();
    if(uint32_t(millis()-streamAt)>=30000){stop();Serial.println("OFF. 30 s shadow session finished.");}
    else if(!fresh()){stop();Serial.println("ERROR: stale/invalid attitude; shadow stopped.");}
    else if(int32_t(now-nextPolicy)>=0){
      lateUs=now-nextPolicy;if(lateUs>maxLateUs)maxLateUs=lateUs;
      if(lateUs>=10000)++lateFrames;
      nextPolicy+=(lateUs/20000+1)*20000;
      infer();report();
    }
  }
  delay(1);
}
