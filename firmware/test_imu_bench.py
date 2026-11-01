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
constexpr int D0=0,D1=1,D2=2,VBAT_ENABLE=14,PIN_CHARGING_CURRENT=22,PIN_VBAT=32;
constexpr int PIN_LSM6DS3TR_C_POWER=15,LOW=0,HIGH=1,INPUT=0,OUTPUT=1,AR_INTERNAL_3_0=1;
inline uint64_t clockUs=0;
inline int levels[33]={},modes[33]={};
inline uint32_t micros(){return uint32_t(clockUs);}
inline uint32_t millis(){return uint32_t(clockUs/1000);}
inline void delay(uint32_t ms){clockUs+=uint64_t(ms)*1000;}
inline void digitalWrite(int p,int v){if(p==D0||p==D1)assert(v==LOW);levels[p]=v;}
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
 template<class T> void print(T v){output<<v;}
 template<class T> void print(T v,int){output<<v;}
 template<class T> void println(T v){output<<v<<'\n';}
 void send(const std::string &s){for(char c:s)rx.push_back(c);}
};
inline FakeSerial Serial;
'''
WIRE = r'''
#pragma once
#include <array>
#include <vector>
#include <deque>
struct FakeWire {
 std::array<uint8_t,256> regs{};
 std::vector<uint8_t> tx;std::deque<uint8_t> rx;
 uint8_t attached=0x6a,address=0,reg=0;
 bool shortRead=false,nack=false,resetStuck=false;
 void reset(){regs.fill(0);regs[0x0f]=0x6a;regs[0x1e]=3;shortRead=nack=resetStuck=false;attached=0x6a;}
 void begin(){}
 void setClock(uint32_t){}
 void beginTransmission(uint8_t a){address=a;tx.clear();}
 void write(uint8_t v){tx.push_back(v);}
 uint8_t endTransmission(bool=true){
  if(address!=attached||nack)return 2;
  reg=tx.at(0);if(tx.size()==2)regs[reg]=tx[1];return 0;
 }
 uint8_t requestFrom(uint8_t a,size_t n){
  rx.clear();if(a!=attached||nack)return 0;
  if(reg==0x12&&!resetStuck)regs[0x12]&=~1;
  size_t count=shortRead?n-1:n;
  for(size_t i=0;i<count;++i)rx.push_back(regs[reg+i]);return count;
 }
 int available(){return rx.size();}
 int read(){int v=rx.front();rx.pop_front();return v;}
 void raw(int axis,int value){uint16_t v=value;regs[0x22+axis*2]=v&255;regs[0x23+axis*2]=v>>8;}
};
inline FakeWire Wire1;
'''
TEST = r'''
#include "imu_bench.ino"
#include <iostream>
int main(){
 Wire1.reset();setup();loop();
 assert(imu.ready&&imu.address==0x6a&&imu.identity==0x6a);
 assert(levels[D0]==LOW&&levels[D1]==LOW&&modes[D0]==OUTPUT&&modes[D1]==OUTPUT);
 assert(levels[VBAT_ENABLE]==LOW&&levels[PIN_CHARGING_CURRENT]==LOW);
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
 Wire1.regs[0x1e]=3;imu.poll();Serial.send("stream\n");loop();assert(streaming);
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
    (folder/'Wire.h').write_text(WIRE)
    (folder/'Adafruit_TinyUSB.h').write_text('')
    for name in ('Lsm6ds3.h','imu_bench.ino'):
        (folder/name).write_bytes((HERE/'imu_bench'/name).read_bytes())
    (folder/'test.cpp').write_text(TEST)
    subprocess.run(['c++','-std=c++17','-I',str(folder),str(folder/'test.cpp'),'-o',str(folder/'test')],check=True)
    subprocess.run([str(folder/'test')],check=True)
