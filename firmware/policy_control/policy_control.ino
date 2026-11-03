// Boot disarmed. USB-supervised trials or explicitly latched standalone operation.
#include <Arduino.h>
#include <Adafruit_TinyUSB.h>
#include <string.h>
#include <stdio.h>
#include "../imu_bench/Lsm6ds3.h"
#include "../policy_shadow/GravityFilter.h"
#include "../policy_shadow/MicrosecondClock.h"
#include "../policy_shadow/MountCalibration.h"
#include "../servo_center/FineServo.h"
#include "ServoProfile.h"
#include "../../sim/recovery/results/policy_simulation_only.h"
#ifndef TARGET_SEEED_XIAO_NRF52840_SENSE
#error "Use the classic XIAO nRF52840 Sense, Seeed non-mbed core."
#endif

enum Mode { OFF=0, HOLD=1, RUN=2, SHADOW=3, STANDALONE=4, CHARGE=5 };
Mode mode=OFF;
const char* lastStopReason="Boot disarmed.";
Lsm6ds3 imu;
GravityFilter attitude;
MicrosecondClock clockUs;
FineServo motors[2];
float accelBase[3]={},gyroBase[3]={},observation[10]={},action[2]={},target[2]={},previous[2]={};
uint16_t pulses[2]={},batteryMv=0;
uint32_t sampleAt=0,lastPoll=0,batteryAt=0,heartbeatAt=0,armedAt=0,runAt=0,nextPolicy=0;
uint32_t frames=0,inferenceUs=0,lateUs=0,dropped=0,filterRejects=0;
uint8_t lowCount=0;
bool hadSerial=false,discard=false;
char command[24];size_t used=0;
const char* HEADER="frame,t_us,mode,obs0_u6,obs1_u6,obs2_u6,obs3_u6,obs4_u6,obs5_u6,obs6_u6,obs7_u6,obs8_u6,obs9_u6,action0_u6,action1_u6,target0_urad,target1_urad,pwm0_us,pwm1_us,battery_mv,inference_us,late_us,sample_age_us,sample_seq,i2c_errors,dropped,filter_rejects";

uint16_t readBatteryMv(){
  analogReference(AR_INTERNAL_3_0);analogReadResolution(12);analogSampleTime(40);
  (void)analogRead(PIN_VBAT);uint32_t sum=0;
  for(int i=0;i<8;++i)sum+=analogRead(PIN_VBAT);
  return uint16_t((uint64_t(sum)*3000*1510)/(8ULL*4096*510));
}
float clip(float v){return fminf(1.f,fmaxf(-1.f,v));}
void resetPolicy(){
  for(int i=0;i<2;++i){target[i]=previous[i]=action[i]=0;pulses[i]=0;}
  frames=inferenceUs=lateUs=dropped=0;
}
void stop(){
  for(int i=0;i<2;++i)if(motors[i].attached())motors[i].detach();
  digitalWrite(D0,LOW);pinMode(D0,OUTPUT);digitalWrite(D1,LOW);pinMode(D1,OUTPUT);pinMode(D2,INPUT);
  mode=OFF;resetPolicy();
}
void halt(const char* reason){stop();lastStopReason=reason;if(Serial){Serial.print("OFF: ");Serial.println(reason);}}
void beginCharge(){
  stop(); // Detach both hardware PWM outputs before acknowledging this mode.
  digitalWrite(PIN_CHARGING_CURRENT,LOW);pinMode(PIN_CHARGING_CURRENT,OUTPUT);
  batteryMv=readBatteryMv();mode=CHARGE;
  lastStopReason="Charge mode: PWM off; servo power remains connected.";
  Serial.println("CHARGE: PWM stopped and held LOW. Switch ON + USB required to charge; net charging not measured.");
}
bool fresh(){return imu.ready&&attitude.ready&&sampleAt&&uint32_t(clockUs.now()-sampleAt)<20000;}
bool validStartBattery(){batteryMv=readBatteryMv();return batteryMv>=3700&&batteryMv<=4400;}
void status(){
  Serial.println("ROBOT POLICY CONTROL 0.3");
  Serial.print("MODE: ");Serial.println(int(mode));
  Serial.print("IMU_READY: ");Serial.println(imu.ready?1:0);
  Serial.print("FILTER_READY: ");Serial.println(attitude.ready?1:0);
  Serial.println("RANGE: trained +/-80 deg; approximate extrapolated PWM 789..2211 us.");
  Serial.println("PROFILE: 50 Hz, action increment 0.06 rad; both measured PWM signs negative.");
  Serial.println("GUARDS: USB trials need heartbeat and have 60 s limit; standalone keeps sensor/timing/battery stops.");
  Serial.print("LAST_STOP: ");Serial.println(lastStopReason);
  Serial.println("POWER: stop/charge remove PWM only. Rev C master switch OFF + USB unplugged is full OFF.");
  Serial.println("Commands: arm, run, standalone, charge (PWM off), shadow (no PWM), keep, off, !, state (non-stopping), status, help");
  Serial.println("READY");
}
void arm(){
  stop();
  if(!fresh()){Serial.println("REFUSED: IMU/filter is not fresh and ready.");return;}
  if(!validStartBattery()){Serial.println("REFUSED: battery start guard, 3700..4400 mV.");return;}
  for(int i=0;i<2;++i){
    if(motors[i].attach(i==0?D0:D1,500,2500)==INVALID_SERVO){halt("PWM attach failed.");return;}
    pulses[i]=1500;motors[i].writeMicroseconds(1500);
  }
  mode=HOLD;armedAt=clockUs.now();heartbeatAt=millis();lowCount=0;
  Serial.println("ARMED: both joints at nominal 1500 us. Wait one second, then run.");
}
void beginControl(bool shadow,bool standalone=false){
  if(!shadow && (mode!=HOLD||uint32_t(clockUs.now()-armedAt)<1000000)){
    halt("run requires arm and one-second neutral hold.");return;
  }
  if(!fresh()){halt("IMU/filter stale or invalid.");return;}
  if(!shadow&&!validStartBattery()){halt("battery start guard.");return;}
  if(shadow)stop();
  // Print before starting policy deadlines: no blocking print during live control.
  Serial.println(HEADER);
  if(shadow){mode=SHADOW;}else{mode=standalone?STANDALONE:RUN;}
  if(standalone)Serial.println("STANDALONE: running; USB may be unplugged. Rev C: switch OFF after unplugging USB for full OFF.");
  runAt=heartbeatAt=millis();nextPolicy=clockUs.now()+20000;lowCount=0;
}
bool appendInteger(char* row,size_t& n,long value){
  const int count=snprintf(row+n,256-n,",%ld",value);
  if(count<0||size_t(count)>=256-n)return false;
  n+=size_t(count);return true;
}
bool appendUnsigned(char* row,size_t& n,uint32_t value){
  const int count=snprintf(row+n,256-n,",%lu",static_cast<unsigned long>(value));
  if(count<0||size_t(count)>=256-n)return false;
  n+=size_t(count);return true;
}
void report(){
  if(!Serial)return; // Intentional USB absence is not lost telemetry.
  char row[256];row[0]='D';size_t n=1;bool ok=true;
  ok &= appendUnsigned(row,n,uint32_t(frames));ok &= appendUnsigned(row,n,uint32_t(sampleAt));
  ok &= appendUnsigned(row,n,uint32_t(mode));
  for(int i=0;i<10;++i)ok &= appendInteger(row,n,lroundf(observation[i]*1e6f));
  for(int i=0;i<2;++i)ok &= appendInteger(row,n,lroundf(action[i]*1e6f));
  for(int i=0;i<2;++i)ok &= appendInteger(row,n,lroundf(target[i]*1e6f));
  for(int i=0;i<2;++i)ok &= appendInteger(row,n,pulses[i]);
  ok &= appendInteger(row,n,batteryMv);ok &= appendUnsigned(row,n,uint32_t(inferenceUs));
  ok &= appendUnsigned(row,n,uint32_t(lateUs));ok &= appendUnsigned(row,n,uint32_t(clockUs.now()-sampleAt));
  ok &= appendUnsigned(row,n,uint32_t(imu.sequence));ok &= appendUnsigned(row,n,uint32_t(imu.errors));
  ok &= appendUnsigned(row,n,uint32_t(dropped));ok &= appendUnsigned(row,n,uint32_t(filterRejects));
  if(!ok||n+1>=sizeof(row)||Serial.availableForWrite()<int(n+1)){++dropped;return;}
  row[n++]='\n';
  if(Serial.write(reinterpret_cast<const uint8_t*>(row),n)!=n)++dropped;
}
bool infer(){
  for(int i=0;i<3;++i)if(!isfinite(attitude.down[i])||!isfinite(gyroBase[i])){halt("non-finite sensor input.");return false;}
  for(int i=0;i<2;++i)if(!isfinite(target[i])||!isfinite(previous[i])){halt("non-finite policy state.");return false;}
  for(int i=0;i<3;++i){observation[i]=clip(attitude.down[i]);observation[i+3]=clip(gyroBase[i]/10.f);}
  for(int i=0;i<2;++i){observation[i+6]=clip(target[i]/CONTROL_LIMIT_RAD);observation[i+8]=previous[i];}
  for(float value:observation)if(!isfinite(value)){halt("non-finite observation.");return false;}
  uint32_t at=clockUs.now();robot_policy(observation,action);inferenceUs=clockUs.now()-at;
  uint16_t proposed[2];
  for(int i=0;i<2;++i){
    if(!isfinite(action[i])){halt("non-finite action.");return false;}
    action[i]=clip(action[i]);
    target[i]=fminf(CONTROL_LIMIT_RAD,fmaxf(-CONTROL_LIMIT_RAD,target[i]+.06f*action[i]));
    if(!controlPulse(target[i],proposed[i])){halt("invalid angle/pulse mapping.");return false;}
  }
  for(int i=0;i<2;++i){
    previous[i]=action[i];
    if(mode==RUN||mode==STANDALONE){pulses[i]=proposed[i];motors[i].writeMicroseconds(pulses[i]);}
  }
  ++frames;return true;
}
void reportState(){
  if(!Serial)return;
  char row[256];
  int n=snprintf(row,sizeof(row),"STATE,%d,%u,%lu,%d,%lu,%s\n",int(mode),unsigned(batteryMv),
    static_cast<unsigned long>(frames),fresh()?1:0,static_cast<unsigned long>(imu.errors),lastStopReason);
  if(n>0&&size_t(n)<sizeof(row)&&Serial.availableForWrite()>=n)
    Serial.write(reinterpret_cast<const uint8_t*>(row),size_t(n));
}
void execute(){
  command[used]=0;
  if(!strcmp(command,"keep")){if(mode!=OFF)heartbeatAt=millis();}
  else if(!strcmp(command,"charge"))beginCharge();
  else if(mode==CHARGE&&(!strcmp(command,"run")||!strcmp(command,"standalone")||!strcmp(command,"shadow"))){
    Serial.println("REFUSED: charge mode is latched; explicitly arm to leave charge mode.");
  }
  else if(!strcmp(command,"arm"))arm();
  else if(!strcmp(command,"run"))beginControl(false);
  else if(!strcmp(command,"standalone"))beginControl(false,true);
  else if(!strcmp(command,"state"))reportState();
  else if(mode==CHARGE&&(!strcmp(command,"status")||!strcmp(command,"help")))status();
  else if(!strcmp(command,"shadow"))beginControl(true);
  else{stop();lastStopReason="Operator stop or command.";Serial.println("OFF. PWM stopped; servo supply may remain powered.");
    if(strcmp(command,"off"))status();}
}
void setup(){
  stop();digitalWrite(VBAT_ENABLE,LOW);pinMode(VBAT_ENABLE,OUTPUT);
  digitalWrite(PIN_CHARGING_CURRENT,LOW);pinMode(PIN_CHARGING_CURRENT,OUTPUT);
  Serial.begin(115200);clockUs.begin();imu.begin();batteryMv=readBatteryMv();
}
void loop(){
  uint32_t now=clockUs.now();
  if(uint32_t(now-lastPoll)>=750){
    lastPoll=now;
    if(imu.poll()){
      uint32_t stamp=clockUs.now();float dt=sampleAt?float(uint32_t(stamp-sampleAt))*1e-6f:0;
      sampleAt=stamp;imuToBase(imu.sample.accelG,accelBase);gyroToBase(imu.sample.gyroRadS,gyroBase);
      bool gyroClip=false,accelClip=false;
      for(int i=0;i<3;++i){gyroClip|=fabsf(imu.sample.gyroRadS[i])>=39.95f;accelClip|=fabsf(imu.sample.accelG[i])>=7.9788f;}
      if(!attitude.update(accelBase,gyroBase,dt,gyroClip,accelClip))++filterRejects;
    }
  }
  const bool connected=bool(Serial);
  if(!connected){
    if(mode!=STANDALONE&&mode!=CHARGE)stop();
    hadSerial=false;used=0;discard=false;
    if(mode!=STANDALONE&&mode!=CHARGE){delay(1);return;}
  }
  if(connected&&!hadSerial){
    // A USB/DTR reconnect must not reset targets or block an active standalone loop.
    if(mode!=STANDALONE)status();
    hadSerial=true;
  }
  if(uint32_t(millis()-batteryAt)>=100){
    batteryAt=millis();batteryMv=readBatteryMv();
    if(mode==HOLD||mode==RUN||mode==STANDALONE){
      if(batteryMv<3600)++lowCount;else lowCount=0;
      if(batteryMv<3400||batteryMv>4400||lowCount>=2)halt("battery guard. Unplug USB and isolate battery (Rev C: slide OFF).");
    }
  }
  for(int n=0;connected&&n<64&&Serial.available();++n){
    char c=Serial.read();
    if(c=='!'){stop();lastStopReason="Emergency PWM stop.";used=0;discard=true;Serial.println("OFF. Emergency PWM stop.");}
    else if(c=='\n'||c=='\r'){if(!discard&&used)execute();used=0;discard=false;}
    else if(!discard&&used<sizeof(command)-1)command[used++]=c;
    else if(!discard){stop();used=0;discard=true;Serial.println("OFF: command too long.");}
  }
  if(mode!=OFF&&mode!=CHARGE){
    if(!fresh())halt("stale/invalid IMU/filter.");
    else if(mode!=STANDALONE&&uint32_t(millis()-heartbeatAt)>=3000)halt("host heartbeat timeout.");
    else if((mode==RUN||mode==SHADOW)&&uint32_t(millis()-runAt)>=60000)halt("trial duration limit.");
    else if(mode==HOLD&&uint32_t(clockUs.now()-armedAt)>=10000000)halt("armed hold timeout.");
    else if(mode==RUN||mode==SHADOW||mode==STANDALONE){
      now=clockUs.now();
      if(int32_t(now-nextPolicy)>=0){
        lateUs=now-nextPolicy;
        if(lateUs>=10000)halt("policy deadline over 10 ms late.");
        else{nextPolicy+=20000;if(infer())report();}
      }
    }
  }
  delay(1);
}
