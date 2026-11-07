// One-joint-at-a-time, visually measured pulse calibration. No learned control.
#include <Arduino.h>
#include <Adafruit_TinyUSB.h>
#include "../servo_center/FineServo.h"
#include <string.h>

#ifndef TARGET_SEEED_XIAO_NRF52840_SENSE
#error "Select the classic Seeed XIAO nRF52840 Sense / non-mbed core."
#endif

FineServo servo;
int selected=-1, targetUs=1500, pulseUs=1500, windowMin=1000, windowMax=2000;
uint16_t batteryMv=0;
uint8_t lowCount=0;
uint32_t startedAt=0, heartbeatAt=0, rampAt=0, batteryAt=0, reportAt=0;
bool hadSerial=false, discard=false;
char command[48];size_t used=0;
constexpr uint32_t HEARTBEAT_MS=5000, SESSION_MS=120000;

uint16_t readBatteryMv(){
  analogReference(AR_INTERNAL_3_0);analogReadResolution(12);analogSampleTime(40);
  (void)analogRead(PIN_VBAT);uint32_t sum=0;
  for(int i=0;i<8;++i)sum+=analogRead(PIN_VBAT);
  return uint16_t((uint64_t(sum)*3000*1510)/(8ULL*4096*510));
}
void stop(){
  if(servo.attached())servo.detach();
  digitalWrite(D8,LOW);pinMode(D8,OUTPUT);
  digitalWrite(D7,LOW);pinMode(D7,OUTPUT);pinMode(D2,INPUT);
  selected=-1;
}
void report(){
  Serial.print("DATA,");Serial.print(millis());Serial.print(',');Serial.print(selected);
  Serial.print(',');Serial.print(targetUs);Serial.print(',');Serial.print(pulseUs);
  Serial.print(',');Serial.println(batteryMv);
}
void status(){
  Serial.println("ROBOT SERVO CALIBRATION 0.1");
  Serial.println("REV_B_DIRECT: PWM stop does not disconnect servo power.");
  Serial.print("ACTIVE_JOINT: ");Serial.println(selected);
  Serial.print("WINDOW_US: ");Serial.print(windowMin);Serial.print(',');Serial.println(windowMax);
  Serial.println("CONTROL: one joint, 50 Hz PWM, 100 us/s commanded slew, heartbeat 5 s, maximum session 120 s.");
  Serial.println("START: first pulse is 1500 us; actual starting angle is unknown. Support both links.");
  Serial.println("Commands: lower, upper, set N, window MIN MAX (off only), keep, status, off, !, help");
  Serial.println("READY");
}
bool number(const char*& text,int& value){
  if(*text<'0'||*text>'9')return false;
  value=0;
  while(*text>='0'&&*text<='9'){
    value=value*10+(*text++-'0');if(value>10000)return false;
  }
  return true;
}
void beginJoint(int joint){
  stop();batteryMv=readBatteryMv();
  if(batteryMv<3700||batteryMv>4400){Serial.println("REFUSED: battery start guard (3700-4400 mV). No PWM.");return;}
  targetUs=pulseUs=1500;
  if(servo.attach(joint==0?D8:D7,500,2500)==INVALID_SERVO){stop();Serial.println("ERROR: PWM attach failed.");return;}
  selected=joint;servo.writeMicroseconds(1500);
  startedAt=heartbeatAt=rampAt=batteryAt=reportAt=millis();lowCount=0;
  Serial.println("ACK: selected joint at nominal 1500 us. Other joint receives no PWM.");report();
}
void execute(){
  command[used]=0;
  if(!strcmp(command,"lower"))beginJoint(0);
  else if(!strcmp(command,"upper"))beginJoint(1);
  else if(!strcmp(command,"keep")){if(selected>=0)heartbeatAt=millis();}
  else if(!strcmp(command,"status")){batteryMv=readBatteryMv();status();report();}
  else if(!strncmp(command,"set ",4)){
    const char* p=command+4;int value=0;
    if(!number(p,value)||*p||selected<0||value<windowMin||value>windowMax||
       value-targetUs>50||targetUs-value>50){
      stop();Serial.println("OFF: invalid set; active joint, window and <=50 us target change required.");
    }else{targetUs=value;Serial.println("ACK: target updated.");report();}
  }else if(!strncmp(command,"window ",7)){
    const char* p=command+7;int lo=0,hi=0;
    const bool valid=number(p,lo)&&*p++==' '&&number(p,hi)&&!*p;
    if(!valid||selected>=0||lo<500||hi>2500||lo>1500||hi<1500||lo>=hi){
      stop();Serial.println("OFF: invalid window; disarm first; 500<=MIN<=1500<=MAX<=2500.");
    }else{windowMin=lo;windowMax=hi;Serial.println("ACK: command window updated; physical clearance still unmeasured.");}
  }else{
    stop();Serial.println("OFF. PWM stopped; direct power remains connected.");
    if(!strcmp(command,"help"))status();
    else if(strcmp(command,"off"))Serial.println("ERROR: unknown command.");
  }
}
void setup(){
  stop();digitalWrite(VBAT_ENABLE,LOW);pinMode(VBAT_ENABLE,OUTPUT);
  digitalWrite(PIN_CHARGING_CURRENT,LOW);pinMode(PIN_CHARGING_CURRENT,OUTPUT);
  Serial.begin(115200);
}
void loop(){
  if(!Serial){stop();hadSerial=false;used=0;discard=false;delay(1);return;}
  if(!hadSerial){stop();hadSerial=true;status();}
  uint32_t now=millis();
  if(selected>=0){
    if(uint32_t(now-startedAt)>=SESSION_MS||uint32_t(now-heartbeatAt)>=HEARTBEAT_MS){
      stop();Serial.println("OFF: session or heartbeat timeout; direct power remains connected.");
    }else if(uint32_t(now-batteryAt)>=100){
      batteryAt=now;batteryMv=readBatteryMv();
      if(batteryMv<3600)++lowCount;else lowCount=0;
      if(batteryMv<3400||batteryMv>4400||lowCount>=2){stop();Serial.println("OFF: battery guard. Disconnect battery and USB.");}
    }
  }
  if(selected>=0){
    // At most one pulse-microsecond per 10 ms; never catch up with a large jump.
    if(uint32_t(now-rampAt)>=10){
      rampAt=now;if(pulseUs<targetUs)++pulseUs;else if(pulseUs>targetUs)--pulseUs;
      servo.writeMicroseconds(pulseUs);
    }
    if(uint32_t(now-reportAt)>=50){reportAt=now;report();}
  }
  for(int n=0;n<64&&Serial.available();++n){
    const char c=Serial.read();
    if(c=='!'){stop();used=0;discard=true;Serial.println("OFF. Emergency PWM stop.");}
    else if(c=='\n'||c=='\r'){if(!discard&&used)execute();used=0;discard=false;}
    else if(!discard&&used<sizeof(command)-1)command[used++]=c;
    else if(!discard){stop();used=0;discard=true;Serial.println("OFF: input too long.");}
  }
  delay(1);
}
