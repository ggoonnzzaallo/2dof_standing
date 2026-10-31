"""Exercise the actual sketch's arming/shutdown logic with fake GPIO and USB.

Needs a host C++ compiler. This does not simulate PWM hardware or USB timing.
"""
from pathlib import Path
import subprocess
import tempfile

SKETCH = Path(__file__).resolve().parent / 'servo_center' / 'servo_center.ino'
ARDUINO = r'''
#pragma once
#include <cstdint>
#include <cstddef>
#include <deque>
#include <string>
#define TARGET_SEEED_XIAO_NRF52840_SENSE 1
constexpr uint8_t D0=0, D1=1, D2=2, VBAT_ENABLE=14, PIN_CHARGING_CURRENT=22, PIN_VBAT=32;
constexpr int AR_INTERNAL_3_0=1;
inline int adcRaw=1800;
inline void analogReference(int){}
inline void analogReadResolution(int){}
inline void analogSampleTime(int){}
inline int analogRead(int){return adcRaw;}
constexpr int LOW=0, HIGH=1, INPUT=0, OUTPUT=1;
inline uint32_t clockMs=0;
inline int pins[33]={};
inline int modes[33]={};
inline unsigned writes[33]={};
inline uint32_t millis(){return clockMs;}
inline void delay(uint32_t ms){clockMs+=ms;}
inline void digitalWrite(uint8_t pin,int level){pins[pin]=level;++writes[pin];}
inline void pinMode(uint8_t pin,int mode){modes[pin]=mode;}
struct FakeSerial {
  bool open=false;
  std::deque<char> rx;
  explicit operator bool() const{return open;}
  void begin(int){}
  void println(const char*){}
  void print(const char*){}
  void println(unsigned short){}
  int available(){return rx.size();}
  int read(){char c=rx.front();rx.pop_front();return c;}
  void send(const std::string& line){for(char c:line)rx.push_back(c);}
};
inline FakeSerial Serial;
'''
SERVO = r'''
#pragma once
#include <cassert>
#include <cstdint>
#define INVALID_SERVO 255
class FineServo {
 public:
  bool enabled=false, fail=false;
  int pin=-1, pulse=0;
  bool attached(){return enabled;}
  uint8_t attach(int p,int,int){
    if (ROBOT_USE_POWER_SWITCH) assert(pins[D2]==HIGH);
    else assert(modes[D2]==INPUT && writes[D2]==0);
    if(fail)return INVALID_SERVO;
    pin=p;enabled=true;return 0; // Zero is a successful channel index.
  }
  void detach(){assert(enabled);enabled=false;}
  void writeMicroseconds(int us){assert(enabled);pulse=us;}
};
'''
TEST = r'''
#include "servo_center.ino"
#include <cassert>
#include <iostream>

void checkOff(){
  assert(!activeServo.attached() && !secondServo.attached());
  assert(pins[D0]==LOW && pins[D1]==LOW);
  if (USE_SERVO_POWER_SWITCH) assert(pins[D2]==LOW);
  else assert(modes[D2]==INPUT && writes[D2]==0);
  assert(activeMode==0);
}
void send(const std::string& s){Serial.send(s);while(Serial.available())loop();}
void fresh(){
  Serial.open=false;Serial.rx.clear();loop();
  clockMs=0;adcRaw=1800;activeServo.fail=false;secondServo.fail=false;setup();checkOff();
  Serial.open=true;loop();checkOff();
}
int main(){
  // Boot, opening the monitor and malformed input never arm motors.
  fresh();assert(pins[VBAT_ENABLE]==LOW && pins[PIN_CHARGING_CURRENT]==LOW);
  send("lower");checkOff();send("\n");
  assert(activeMode==2 && activeServo.pin==D0);
  if (USE_SERVO_POWER_SWITCH) assert(pins[D2]==HIGH);
  assert(activeServo.pulse==1500);
  send("off\n");checkOff();

  fresh();send("power\n");
  if (USE_SERVO_POWER_SWITCH) {
    assert(pins[D2]==HIGH && !activeServo.attached());
    clockMs=POWER_TEST_MS-1;loop();assert(activeMode==1);
    ++clockMs;loop();checkOff();
  } else checkOff();

  fresh();send("lower\n");clockMs=CENTER_HOLD_MS-1;loop();assert(activeMode==2);
  ++clockMs;loop();checkOff();

  fresh();send("upper\n");assert(activeServo.pin==D1 && activeServo.pulse==1500);
  Serial.open=false;loop();checkOff();
  Serial.open=true;loop();checkOff();

  fresh();send("lower\n");send("!upper\n");checkOff();
  send("upper\n");assert(activeMode==3);send("typo\n");checkOff();

  fresh();send(std::string(40,'x')+"lower\n");checkOff();
  send("lower\n");assert(activeMode==2);send("help\n");checkOff();

  fresh();clockMs=UINT32_MAX-10;send("power\n");
  clockMs+=POWER_TEST_MS;loop();checkOff(); // millis rollover is safe.

  fresh();activeServo.fail=true;send("lower\n");checkOff();
  // Each unloaded jog selects one output, changes target at known times,
  // returns to neutral before detaching, and still honors immediate shutdown.
  for (bool upper : {false, true}) {
    fresh();send(upper ? "upper-jog\n" : "lower-jog\n");
    assert(activeServo.pin==(upper ? D1 : D0));
    assert(pins[upper ? D0 : D1]==LOW);
    assert(activeServo.pulse==1500);
    const int expected[]={1500,1200,1800,1200,1800,1200,1500};
    const uint32_t origin=startedAt;
    for (uint32_t i=1;i<7;++i) {
      clockMs=origin+i*1500-1;loop();
      assert(activeServo.pulse==expected[i-1]);
      ++clockMs;loop();assert(activeServo.pulse==expected[i]);
    }
    clockMs=origin+10499;loop();assert(activeServo.attached() && activeServo.pulse==1500);
    ++clockMs;loop();checkOff();
  }
  fresh();send("lower-jog\n");send("!\n");checkOff();
  fresh();send("upper-jog\n");Serial.open=false;loop();checkOff();
  fresh();clockMs=UINT32_MAX-10;send("lower-jog\n");
  clockMs=startedAt+3000;loop();assert(activeServo.pulse==1800);
  clockMs=startedAt+10500;loop();checkOff();
  for (bool upper : {false, true}) {
    fresh();send(upper ? "upper-small\n" : "lower-small\n");
    assert(activeServo.pin==(upper ? D1 : D0));
    assert(pins[upper ? D0 : D1]==LOW);
    const int expected[]={1500,1450,1500,1550,1500};
    const uint32_t origin=startedAt;
    assert(activeServo.pulse==1500);
    for (uint32_t i=1;i<5;++i) {
      clockMs=origin+i*1500-1;loop();assert(activeServo.pulse==expected[i-1]);
      ++clockMs;loop();assert(activeServo.pulse==expected[i]);
    }
    clockMs=origin+7499;loop();assert(activeServo.attached() && activeServo.pulse==1500);
    ++clockMs;loop();checkOff();
  }
  fresh();send("lower-small\n");clockMs=startedAt+1500;loop();
  send("!\n");checkOff();
  fresh();send("upper-small\n");Serial.open=false;loop();checkOff();
  fresh();clockMs=UINT32_MAX-10;send("upper-small\n");
  clockMs=startedAt+4500;loop();assert(activeServo.pulse==1550);
  clockMs=startedAt+7500;loop();checkOff();
  fresh();send("dance\n");
  assert(activeMode==8 && activeServo.pin==D0 && secondServo.pin==D1);
  const uint32_t origin=startedAt;
  int previousLower=1500,previousUpper=1500;
  for(uint32_t t=0;t<DANCE_HOLD_MS;++t) {
    clockMs=origin+t;loop();
    assert(activeServo.attached() && secondServo.attached());
    // No changes between servo frames; bounded movement even on full reversals.
    if (t%DANCE_UPDATE_MS) {
      assert(activeServo.pulse==previousLower && secondServo.pulse==previousUpper);
    }
    assert(std::abs(activeServo.pulse-previousLower)<=12);
    assert(std::abs(secondServo.pulse-previousUpper)<=12);
    previousLower=activeServo.pulse;previousUpper=secondServo.pulse;
    assert(activeServo.pulse>=1100 && activeServo.pulse<=1900);
    assert(secondServo.pulse>=1100 && secondServo.pulse<=1900);

  }
  assert(activeServo.pulse==1500 && secondServo.pulse==1500);
  clockMs=origin+DANCE_HOLD_MS;loop();checkOff();
  fresh();send("dance\n!\n");checkOff();
  fresh();send("dance\n");Serial.open=false;loop();checkOff();
  fresh();secondServo.fail=true;send("dance\n");checkOff();
  fresh();clockMs=UINT32_MAX-10;send("dance\n");
  clockMs=startedAt+DANCE_HOLD_MS;loop();checkOff();
  fresh();send("battery\n");checkOff();assert(batteryMv>3890 && batteryMv<3920);
  fresh();adcRaw=1600;send("dance-loop\n");checkOff();
  fresh();send("dance-loop\n");assert(activeMode==9);
  clockMs=4000;send("keep\n");assert(activeMode==9);
  clockMs=8000;send("keep\n");assert(activeMode==9);
  clockMs=13000;loop();checkOff();
  fresh();send("dance-loop\n");adcRaw=1600;
  clockMs=100;loop();assert(activeMode==9);
  clockMs=200;loop();checkOff();
  send("dance-loop\n");checkOff(); // Cannot restart while low.
  fresh();send("dance-loop\n");adcRaw=0;clockMs=100;loop();checkOff();
  fresh();send("dance-loop\n!\n");checkOff();
  fresh();send("dance-loop\n");Serial.open=false;loop();checkOff();
  fresh();send("dance-loop\n");
  int previousFastLower=1500,previousFastUpper=1500;
  for(uint32_t t=0;t<60000;++t) {
    clockMs=t;
    if(t%2000==0) send("keep\n"); else loop();
    assert(activeMode==9 && activeServo.attached() && secondServo.attached());
    assert(activeServo.pulse>=1100 && activeServo.pulse<=1900);
    assert(secondServo.pulse>=1100 && secondServo.pulse<=1900);
    assert(std::abs(activeServo.pulse-previousFastLower)<=26);
    assert(std::abs(secondServo.pulse-previousFastUpper)<=26);
    previousFastLower=activeServo.pulse;previousFastUpper=secondServo.pulse;
  }
  send("off\n");checkOff();
  fresh();send("dance-loop\n");
  clockMs=27;loop();assert(lastDanceUpdateMs==25);
  clockMs=40;loop();assert(lastDanceUpdateMs==40); // No drift after a late frame.
  send("off\n");checkOff();
  fresh();send("tempo 1000\n");checkOff();
  fresh();send("dance-loop\n");clockMs=6000;send("keep\n");
  // Above misses the heartbeat deliberately; restart for phase continuity checks.
  send("dance-loop\n");
  clockMs=startedAt+1000;
  const float phaseBefore=tempoPhaseAt(1000),speedBefore=tempoVelocityAt(1000);
  send("tempo 1000\n");
  assert(std::abs(fmodf(phaseBefore,2*PI_F)-tempoPhaseAt(1000))<0.0001f);
  assert(std::abs(speedBefore-tempoVelocityAt(1000))<0.000001f);
  assert(std::abs(tempoVelocityAt(3000)-2*PI_F/1000)<0.000001f);
  send("tempo 99999999999999\n");checkOff();
  fresh();send("dance-loop\n");send("tempo 999\n");checkOff();
  fresh();send("dance-loop\n");send("tempo xyz\n");checkOff();
  std::cout << "PASS: disarmed boot, explicit commands, centering, wide and small jogs, timeouts, "
               "disconnect, emergency stop, malformed input, rollover, attach failure.\n";
}
'''

with tempfile.TemporaryDirectory(prefix='2dof-center-test-') as directory:
    root = Path(directory)
    (root/'Arduino.h').write_text(ARDUINO)
    (root/'Adafruit_TinyUSB.h').write_text('#pragma once\n')
    (root/'FineServo.h').write_text(SERVO)
    (root/'servo_center.ino').write_text(SKETCH.read_text())
    (root/'test.cpp').write_text(TEST)
    for switched in (0, 1):
        print(f'Power profile: {"Rev A switched" if switched else "Rev B direct"}', flush=True)
        binary = root/f'test-{switched}'
        subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror',
                        f'-DROBOT_USE_POWER_SWITCH={switched}',
                        '-I',str(root),str(root/'test.cpp'),'-o',str(binary)],check=True)
        subprocess.run([str(binary)],check=True)
