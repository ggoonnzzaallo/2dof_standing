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
constexpr uint8_t D0=0, D1=1, D2=2, VBAT_ENABLE=14, PIN_CHARGING_CURRENT=22;
constexpr int LOW=0, HIGH=1, OUTPUT=1;
inline uint32_t clockMs=0;
inline int pins[33]={};
inline uint32_t millis(){return clockMs;}
inline void delay(uint32_t ms){clockMs+=ms;}
inline void digitalWrite(uint8_t pin,int level){pins[pin]=level;}
inline void pinMode(uint8_t,int){}
struct FakeSerial {
  bool open=false;
  std::deque<char> rx;
  explicit operator bool() const{return open;}
  void begin(int){}
  void println(const char*){}
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
class Servo {
 public:
  bool enabled=false, fail=false;
  int pin=-1, pulse=0;
  bool attached(){return enabled;}
  uint8_t attach(int p,int,int){
    assert(pins[D2]==HIGH); // No deliberate PWM into an unpowered servo.
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
  assert(!activeServo.attached());
  assert(pins[D0]==LOW && pins[D1]==LOW && pins[D2]==LOW);
  assert(activeMode==0);
}
void send(const std::string& s){Serial.send(s);while(Serial.available())loop();}
void fresh(){
  Serial.open=false;Serial.rx.clear();loop();
  clockMs=0;activeServo.fail=false;setup();checkOff();
  Serial.open=true;loop();checkOff();
}
int main(){
  // Boot, opening the monitor and malformed input never arm motors.
  fresh();assert(pins[VBAT_ENABLE]==LOW && pins[PIN_CHARGING_CURRENT]==LOW);
  send("lower");checkOff();send("\n");
  assert(activeMode==2 && pins[D2]==HIGH && activeServo.pin==D0);
  assert(activeServo.pulse==1500);
  send("off\n");checkOff();

  fresh();send("power\n");assert(pins[D2]==HIGH && !activeServo.attached());
  clockMs=POWER_TEST_MS-1;loop();assert(activeMode==1);
  ++clockMs;loop();checkOff();

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
  std::cout << "PASS: disarmed boot, explicit commands, center-only PWM, timeouts, "
               "disconnect, emergency stop, malformed input, rollover, attach failure.\n";
}
'''

with tempfile.TemporaryDirectory(prefix='2dof-center-test-') as directory:
    root = Path(directory)
    (root/'Arduino.h').write_text(ARDUINO)
    (root/'Adafruit_TinyUSB.h').write_text('#pragma once\n')
    (root/'Servo.h').write_text(SERVO)
    (root/'servo_center.ino').write_text(SKETCH.read_text())
    (root/'test.cpp').write_text(TEST)
    binary = root/'test'
    subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror',
                    '-I',str(root),str(root/'test.cpp'),'-o',str(binary)],check=True)
    subprocess.run([str(binary)],check=True)
