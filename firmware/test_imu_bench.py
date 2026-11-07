"""Exercise real sensor decoding/fault handling and the sensor-only sketch on host.

Fake I2C cannot establish hardware connectivity, timing, bus hang behavior or accuracy.
"""
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ARDUINO = r'''
#pragma once
#include <cstdint>
#include <cstddef>
#include <string>
#include <sstream>
#include <deque>
#include <cassert>
#define TARGET_SEEED_XIAO_NRF52840_SENSE 1
constexpr int D8=8,D7=7,D2=2,VBAT_ENABLE=14,PIN_CHARGING_CURRENT=22,PIN_VBAT=32;
constexpr int PIN_LSM6DS3TR_C_POWER=15,LOW=0,HIGH=1,INPUT=0,OUTPUT=1,AR_INTERNAL_3_0=1;
constexpr int OUTPUT_H0H1=3;
inline uint64_t clockUs=0;
inline uint32_t serialCostUs=0;
inline int levels[33]={},modes[33]={};
inline uint32_t micros(){return uint32_t(clockUs);}
inline uint32_t millis(){return uint32_t(clockUs/1000);}
inline void delay(uint32_t ms){clockUs+=uint64_t(ms)*1000;}
inline void digitalWrite(int p,int v){if(p==D8||p==D7)assert(v==LOW);levels[p]=v;}
inline void pinMode(int p,int m){modes[p]=m;}
inline void analogReference(int){}
inline void analogReadResolution(int){}
inline void analogSampleTime(int){}
inline int analogRead(int){return 1800;}
struct FakeSerial {
 bool open=true;std::deque<char> rx;std::ostringstream output;
 explicit operator bool()const{return open;}
 void begin(int){}
 int available(){return rx.size();}
 int read(){char c=rx.front();rx.pop_front();return c;}
 template<class T> void print(T v){output<<v;clockUs+=serialCostUs;}
 template<class T> void print(T v,int){output<<v;clockUs+=serialCostUs;}
 template<class T> void println(T v){output<<v<<'\n';clockUs+=serialCostUs;}
 void send(const std::string &s){for(char c:s)rx.push_back(c);}
};
inline FakeSerial Serial;
'''
BUS = r'''
#pragma once
#include <array>
struct FakeSensor {
 std::array<uint8_t,256> regs{};
 uint8_t attached=0x6a;
 bool shortRead=false,nack=false,resetStuck=false;
 void reset(){regs.fill(0);regs[0x0f]=0x6a;regs[0x1e]=3;shortRead=nack=resetStuck=false;attached=0x6a;}
 void raw(int axis,int value){uint16_t v=value;regs[0x22+axis*2]=v&255;regs[0x23+axis*2]=v>>8;}
};
inline FakeSensor Wire1;
struct ImuBus {
 uint32_t lastError=0,hardwareError=0;
 void begin(){}
 bool write(uint8_t a,uint8_t reg,uint8_t value){
  if(a!=Wire1.attached||Wire1.nack)return false;
  Wire1.regs[reg]=value;return true;
 }
 bool read(uint8_t a,uint8_t reg,uint8_t *out,size_t n){
  if(a!=Wire1.attached||Wire1.nack||Wire1.shortRead)return false;
  if(reg==0x12&&!Wire1.resetStuck)Wire1.regs[0x12]&=~1;
  for(size_t i=0;i<n;++i)out[i]=Wire1.regs[reg+i];return true;
 }
};
'''
TEST = r'''
#include "imu_bench.ino"
#include <iostream>
int main(){
 Wire1.reset();setup();loop();
 assert(imu.ready&&imu.address==0x6a&&imu.identity==0x6a);
 assert(levels[D8]==LOW&&levels[D7]==LOW&&modes[D8]==OUTPUT&&modes[D7]==OUTPUT);
 assert(levels[VBAT_ENABLE]==LOW&&levels[PIN_CHARGING_CURRENT]==LOW);
 assert(modes[PIN_LSM6DS3TR_C_POWER]==OUTPUT_H0H1&&levels[PIN_LSM6DS3TR_C_POWER]==HIGH);
 // Signed little-endian decode with documented, distinct accelerometer/gyro units.
 Wire1.raw(0,1000);Wire1.raw(1,-1000);Wire1.raw(2,-32768);
 Wire1.raw(3,4098);Wire1.raw(4,-4098);Wire1.raw(5,0);
 assert(imu.poll());
 assert(fabs(imu.sample.gyroRadS[0]-1.2217305f)<1e-6);
 assert(fabs(imu.sample.gyroRadS[1]+1.2217305f)<1e-6);
 assert(imu.sample.gyroRadS[2]<-40&&imu.sample.saturated);
 assert(fabs(imu.sample.accelG[0]-.999912f)<1e-6);
 assert(fabs(imu.sample.accelG[1]+.999912f)<1e-6);
 uint32_t seq=imu.sequence,errors=imu.errors;
 Wire1.shortRead=true;assert(!imu.poll());assert(imu.sequence==seq&&imu.errors>errors);
 Wire1.shortRead=false;Wire1.regs[0x1e]=0;errors=imu.errors;
 assert(!imu.poll()&&imu.sequence==seq&&imu.errors==errors);
 Wire1.regs[0x1e]=3;imu.poll();Serial.send("stream\n");
 serialCostUs=250;loop();assert(streaming);serialCostUs=0;
 Serial.send("!\n");loop();assert(!streaming);
 Serial.send("stream\n");loop();assert(streaming);Serial.open=false;loop();assert(!streaming);
 Serial.open=true;loop();Serial.send("stream\n");loop();assert(streaming);
 Wire1.regs[0x1e]=0;delay(101);loop();assert(!streaming); // Never stream stale samples.
 Wire1.regs[0x1e]=3;loop();Serial.send("stream\n");loop();assert(streaming);
 delay(30000);loop();assert(!streaming); // Bounded stream even with fresh sensor data.
 Wire1.reset();Wire1.regs[0x0f]=0x69;Lsm6ds3 wrong;assert(!wrong.begin()&&!wrong.ready);
 Wire1.reset();Wire1.resetStuck=true;Lsm6ds3 stuck;assert(!stuck.begin());
 Wire1.reset();Wire1.attached=0x6b;Lsm6ds3 other;assert(other.begin()&&other.address==0x6b);
 Wire1.nack=true;seq=other.sequence;assert(!other.poll()&&other.sequence==seq);
 std::cout<<"PASS: sensor identity/configuration, units/signs, short reads, no-new-data, stale/disconnect stops, reset timeout, alternate address, no HIGH servo signals.\n";
}
'''

with tempfile.TemporaryDirectory() as folder:
    folder = Path(folder)
    (folder/'Arduino.h').write_text(ARDUINO)
    (folder/'ImuBus.h').write_text(BUS)
    (folder/'Adafruit_TinyUSB.h').write_text('')
    for name in ('Lsm6ds3.h','imu_bench.ino'):
        (folder/name).write_bytes((HERE/'imu_bench'/name).read_bytes())
    (folder/'test.cpp').write_text(TEST)
    subprocess.run(['c++','-std=c++17','-I',str(folder),str(folder/'test.cpp'),'-o',str(folder/'test')],check=True)
    subprocess.run([str(folder/'test')],check=True)
