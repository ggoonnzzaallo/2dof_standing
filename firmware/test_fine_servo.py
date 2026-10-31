"""Test the actual PWM adapter against a mock of the board core's PWM API."""
from pathlib import Path
import subprocess
import tempfile

MOCK = r'''
#pragma once
#include <cstdint>
constexpr int LOW=0;
inline void digitalWrite(uint8_t,int){}
constexpr int HWPWM_MODULE_NUM=1, PWM_PRESCALER_PRESCALER_DIV_16=4;
class HardwarePWM {
 public:
  uint32_t owner=0;
  int period=0, divider=-1, pins=0, pulses[4]={};
  bool running=false;
  bool isOwner(uint32_t token){return owner==token;}
  bool takeOwnership(uint32_t token){if(owner)return false;owner=token;return true;}
  bool releaseOwnership(uint32_t token){if(pins||owner!=token)return false;owner=0;return true;}
  bool addPin(uint8_t pin){pins|=1<<pin;return true;}
  bool removePin(uint8_t pin){pins&=~(1<<pin);return true;}
  void setClockDiv(int value){divider=value;}
  void setMaxValue(int value){period=value;}
  bool writePin(uint8_t pin,uint16_t value){pulses[pin]=value;running=true;return true;}
  int usedChannelCount(){return __builtin_popcount(pins);}
  void stop(){running=false;}
};
inline HardwarePWM pwm;
inline HardwarePWM* HwPWMx[]={&pwm};
'''
TEST = r'''
#include "FineServo.h"
#include <cassert>
int main(){
 FineServo lower,upper;
 assert(!lower.attached());
 assert(lower.attach(0,1000,2000)!=INVALID_SERVO);
 assert(pwm.period==20000 && pwm.divider==4);
 for(int us=1000;us<=2000;++us){lower.writeMicroseconds(us);assert(pwm.pulses[0]==us);}
 assert(upper.attach(1,1000,2000)!=INVALID_SERVO);
 lower.writeMicroseconds(1500);upper.writeMicroseconds(1501);
 assert(pwm.pulses[0]==1500 && pwm.pulses[1]==1501);
 lower.writeMicroseconds(999);assert(pwm.pulses[0]==1000);
 upper.writeMicroseconds(2001);assert(pwm.pulses[1]==2000);
 lower.detach();assert(!lower.attached() && upper.attached() && pwm.running);
 upper.detach();assert(!upper.attached() && !pwm.running && pwm.owner==0);
 upper.detach(); // idempotent
 pwm.owner=123;
 assert(lower.attach(0,1000,2000)==INVALID_SERVO && !lower.attached());
}
'''
with tempfile.TemporaryDirectory() as directory:
    root=Path(directory)
    (root/'Arduino.h').write_text(MOCK)
    (root/'HardwarePWM.h').write_text('#pragma once\n')
    (root/'FineServo.h').write_text((Path(__file__).parent/'servo_center/FineServo.h').read_text())
    (root/'test.cpp').write_text(TEST)
    subprocess.run(['c++','-std=c++17','-Wall','-Wextra','-Werror','-I',str(root),str(root/'test.cpp'),'-o',str(root/'test')],check=True)
    subprocess.run([str(root/'test')],check=True)
print('PASS: 1 us pulse resolution, 50 Hz period, two channels, clamp, stop, ownership failure.')
