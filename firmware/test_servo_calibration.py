"""Test actual calibration sketch: bounded single-joint movement and stop paths."""
from pathlib import Path
import ast
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
source = ast.parse((HERE / 'test_servo_center.py').read_text())
fixtures = {node.targets[0].id: ast.literal_eval(node.value) for node in source.body
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)}
arduino = fixtures['ARDUINO'].replace('  void println(unsigned short){}',
    '  template<typename T> void print(T){}\n  template<typename T> void println(T){}')
TEST = r'''
#include "firmware/servo_calibration/servo_calibration.ino"
#include <cassert>
#include <iostream>
void checkOff(){
 assert(selected==-1&&!servo.attached());assert(pins[D0]==LOW&&pins[D1]==LOW);
 assert(modes[D2]==INPUT&&writes[D2]==0);
}
void send(const char* s){Serial.send(s);while(Serial.available())loop();}
void reset(){
 Serial.open=false;Serial.rx.clear();loop();clockMs=0;adcRaw=1800;
 servo.fail=false;windowMin=1000;windowMax=2000;setup();checkOff();
 Serial.open=true;loop();checkOff();
}
int main(){
 reset();send("status\n");checkOff();send("keep\n");checkOff();
 send("lower\n");assert(selected==0&&servo.pin==D0&&servo.pulse==1500&&pins[D1]==LOW);
 send("set 1550\n");assert(targetUs==1550&&pulseUs==1500);
 int previous=pulseUs;
 for(int i=0;i<50;++i){clockMs+=10;loop();assert(pulseUs-previous==1);previous=pulseUs;}
 assert(pulseUs==1550);
 send("set 1500\n");clockMs+=3000;loop();assert(pulseUs==1549); // No catch-up jump.
 send("off\n");checkOff();
 reset();send("upper\n");assert(selected==1&&servo.pin==D1&&pins[D0]==LOW);
 send("set 1551\n");checkOff(); // Target changes larger than 50 us are rejected.
 reset();send("lower\n");send("window 500 2500\n");checkOff();assert(windowMin==1000);
 send("window 500 2500\n");assert(windowMin==500&&windowMax==2500);checkOff();
 send("upper\n");for(int p=1550;p<=2500;p+=50){
  char b[30];snprintf(b,sizeof(b),"set %d\n",p);send(b);assert(targetUs==p);send("keep\n");
 }
 send("set 2501\n");checkOff();
 for(const char* invalid:{"set 1000x\n","window 499 2500\n","window 500 2501\n","window 2000 1000\n","window 500\n","set 999999999999\n","typo\n"}){
  reset();send("lower\n");send(invalid);checkOff();
 }
 reset();send("lower\n");send("!upper\n");checkOff();
 send("upper\n");Serial.open=false;loop();checkOff();
 reset();send("lower\n");clockMs=heartbeatAt+HEARTBEAT_MS;loop();checkOff();
 reset();send("lower\n");clockMs=startedAt+SESSION_MS;send("keep\n");checkOff();
 reset();clockMs=UINT32_MAX-100;send("lower\n");clockMs+=200;loop();assert(selected==0);
 clockMs=heartbeatAt+HEARTBEAT_MS;loop();checkOff();
 reset();adcRaw=1500;send("lower\n");checkOff(); // Low battery refuses start.
 reset();send("lower\n");adcRaw=1600;clockMs+=101;loop();assert(selected==0);
 clockMs+=101;loop();checkOff(); // Two <3.6 V samples.
 reset();send("upper\n");adcRaw=0;clockMs+=101;loop();checkOff();
 reset();servo.fail=true;send("lower\n");checkOff();
 reset();send("lower\n");send("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxupper\n");checkOff();
 std::cout<<"PASS: disarmed boot, single-joint PWM, 1 us slew steps, no late catch-up, target/window/parser bounds, battery guards, emergency/disconnect/timeouts and clock rollover.\n";
}
'''
with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    (root / 'firmware/servo_calibration').mkdir(parents=True)
    (root / 'firmware/servo_center').mkdir(parents=True)
    (root / 'Arduino.h').write_text(arduino)
    (root / 'Adafruit_TinyUSB.h').write_text('')
    (root / 'firmware/servo_center/FineServo.h').write_text(fixtures['SERVO'])
    sketch = HERE / 'servo_calibration/servo_calibration.ino'
    (root / 'firmware/servo_calibration/servo_calibration.ino').write_bytes(sketch.read_bytes())
    (root / 'test.cpp').write_text(TEST)
    subprocess.run(['c++', '-std=c++17', '-Wall', '-Wextra', '-Werror', '-DROBOT_USE_POWER_SWITCH=0',
                    '-I', str(root), str(root / 'test.cpp'), '-o', str(root / 'test')], check=True)
    subprocess.run([str(root / 'test')], check=True)
