"""Test the actual learned controller, sensor pipeline and PWM against fake hardware."""
import ast
import csv
import io
import sys
from pathlib import Path
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
source=ast.parse((HERE/'test_imu_bench.py').read_text())
fixtures={node.targets[0].id:ast.literal_eval(node.value) for node in source.body
          if isinstance(node,ast.Assign) and isinstance(node.value,ast.Constant) and isinstance(node.value.value,str)}
arduino=fixtures['ARDUINO'].replace('clockUs','fakeTimeUs')
arduino=arduino.replace('inline int analogRead(int){return 1800;}','inline int adcRaw=1800;\ninline int analogRead(int){return adcRaw;}')
arduino=arduino.replace(' bool open=true;', ' int txAvailable=256;\n bool open=true;')
arduino=arduino.replace(' void begin(int){}',' void begin(int){}\n int availableForWrite(){return txAvailable;}\n size_t write(const uint8_t* b,size_t n){output.write(reinterpret_cast<const char*>(b),n);return n;}')
clock='#pragma once\nstruct MicrosecondClock {void begin(){} uint32_t now()const{return uint32_t(fakeTimeUs);}};\n'
servo='''#pragma once
#include <cassert>
constexpr uint8_t INVALID_SERVO=255;
class FineServo {
 public:
 bool on=false,fail=false;int pin=-1,pulse=0,writes=0;
 bool attached()const{return on;}
 uint8_t attach(int p,int lo,int hi){assert(p==D8||p==D7);assert(lo==500&&hi==2500);if(fail)return INVALID_SERVO;on=true;pin=p;return 0;}
 void detach(){assert(on);on=false;}
 void writeMicroseconds(int us){assert(on&&us>=789&&us<=2211);pulse=us;++writes;}
};
'''
test=r'''
#include "firmware/policy_control/policy_control.ino"
#include <cassert>
#include <iostream>
#include <limits>
#include <fstream>
void checkOff(){assert(mode==OFF&&!motors[0].attached()&&!motors[1].attached());assert(levels[D8]==LOW&&levels[D7]==LOW);}
void send(const char* text){Serial.send(text);while(Serial.available())loop();}
void resetFixture(uint64_t origin=0){
 stop();fakeTimeUs=origin;serialCostUs=0;Serial.open=true;Serial.txAvailable=256;Serial.rx.clear();Serial.output.str("");Serial.output.clear();
 adcRaw=1800;Wire1.reset();Wire1.raw(5,4098);imu=Lsm6ds3();attitude=GravityFilter();
 hadSerial=false;discard=false;used=0;sampleAt=lastPoll=batteryAt=0;filterRejects=0;
 for(auto& motor:motors)motor=FineServo();setup();for(int i=0;i<22;++i){delay(5);loop();}
 checkOff();assert(fresh());
}
void waitMs(int ms){uint32_t start=millis();while(uint32_t(millis()-start)<uint32_t(ms)){delay(1);loop();}}
void running(){resetFixture();send("arm\n");assert(mode==HOLD);waitMs(1100);send("run\n");assert(mode==RUN);}
int main(int argc,char** argv){
 uint16_t value=0;assert(controlPulse(0,value)&&value==1500);
 assert(controlPulse(CONTROL_LIMIT_RAD,value)&&value==789);
 assert(controlPulse(-CONTROL_LIMIT_RAD,value)&&value==2211);
 assert(controlPulse(.7853981634f,value)&&value==1100);
 assert(!controlPulse(1.5f,value)&&!controlPulse(std::numeric_limits<float>::quiet_NaN(),value));
 resetFixture();send("run\n");checkOff();
 resetFixture();send("arm\n");assert(mode==HOLD&&motors[0].pulse==1500&&motors[1].pulse==1500);
 assert(motors[0].pin==8&&motors[1].pin==7); // Actual joint ordering, not just allowed pins.
 send("run\n");checkOff(); // One-second neutral acquisition is mandatory.
 running();for(int i=0;i<100;++i){
   waitMs(20);assert(mode==RUN);if(i%10==0)send("keep\n");
   for(int j=0;j<2;++j){assert(fabsf(target[j])<=CONTROL_LIMIT_RAD);assert(controlPulse(target[j],value)&&motors[j].pulse==value);}
 }
 assert(frames>=100&&inferenceUs<20000);
 if(argc>1){std::ofstream capture(argv[1]);capture<<Serial.output.str();}
 send("off\n");checkOff();
 resetFixture();send("shadow\n");assert(mode==SHADOW);waitMs(100);
 assert(frames==5&&!motors[0].attached()&&!motors[1].attached()&&pulses[0]==0&&pulses[1]==0);
 resetFixture();adcRaw=1500;send("arm\n");checkOff();
 running();adcRaw=1600;waitMs(250);checkOff();
 running();adcRaw=0;waitMs(110);checkOff();
 resetFixture();motors[1].fail=true;send("arm\n");checkOff();
 running();Wire1.regs[0x1e]=0;waitMs(30);checkOff();
 running();attitude=GravityFilter();send("keep\n");checkOff();
 running();target[0]=std::numeric_limits<float>::quiet_NaN();delay(20);loop();checkOff();
 running();Serial.open=false;loop();checkOff();
 running();send("!run\n");checkOff();
 running();send("typo\n");checkOff();
 running();send("xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxrun\n");checkOff();
 running();heartbeatAt=millis()-3000;loop();checkOff();
 running();runAt=millis()-60000;loop();checkOff();
 running();nextPolicy=clockUs.now()-10001;loop();checkOff();
 running();Serial.txAvailable=0;waitMs(100);assert(mode==RUN&&dropped>=5); // Never block for telemetry.
 Serial.txAvailable=256;waitMs(20);assert(mode==RUN);
 for(int i=0;i<2;++i)target[i]=CONTROL_LIMIT_RAD;assert(infer());
 for(int i=0;i<2;++i)assert(motors[i].pulse>=789&&motors[i].pulse<=2211);
 Serial.output.str("");Serial.output.clear();
 frames=sampleAt=imu.sequence=imu.errors=dropped=filterRejects=0xffffffff;
 inferenceUs=lateUs=0xffffffff;for(int i=0;i<10;++i)observation[i]=-1;
 for(int i=0;i<2;++i){target[i]=-CONTROL_LIMIT_RAD;action[i]=-1;}
 report();assert(!Serial.output.str().empty()&&Serial.output.str().size()<=256); // Maximal telemetry still fits board TX FIFO.
 resetFixture((1ULL<<32)-160000);send("arm\n");waitMs(1100);send("run\n");waitMs(100);assert(mode==RUN&&frames==5);

 // Standalone is an explicit transition: not boot, disconnect, keep or early command.
 resetFixture();send("standalone\n");checkOff();
 resetFixture();send("arm\n");send("standalone\n");checkOff();
 resetFixture();send("arm\n");waitMs(1100);send("standalone\n");assert(mode==STANDALONE);
 uint32_t before=frames;float priorTarget=target[0];
 Serial.open=false;waitMs(200);assert(mode==STANDALONE&&frames>=before+10);
 assert(motors[0].attached()&&motors[1].attached());
 heartbeatAt=millis()-5000;runAt=millis()-65000;waitMs(100);
 assert(mode==STANDALONE); // Neither USB heartbeat nor supervised trial deadline applies.
 before=frames;waitMs(61000);assert(mode==STANDALONE&&frames>=before+3050);
 Serial.open=true;before=frames;loop();assert(mode==STANDALONE&&frames>=before);
 send("state\n");assert(mode==STANDALONE);waitMs(100);assert(frames>before);
 send("off\n");checkOff();
 resetFixture();send("arm\n");waitMs(1100);send("standalone\n");Serial.open=false;
 adcRaw=1600;waitMs(250);checkOff();assert(std::string(lastStopReason).find("battery")!=std::string::npos);
 waitMs(100);checkOff();Serial.open=true;loop();checkOff(); // Fault never automatically rearms.
 resetFixture();send("arm\n");waitMs(1100);send("standalone\n");Serial.open=false;
 Wire1.regs[0x1e]=0;waitMs(30);checkOff();
 resetFixture();send("arm\n");waitMs(1100);send("standalone\n");Serial.open=false;
 nextPolicy=clockUs.now()-10001;loop();checkOff();
 resetFixture();send("arm\n");waitMs(1100);send("standalone\n");Serial.open=false;waitMs(200);
 Serial.open=true;send("!\n");checkOff();
 // Charging stops active PWM immediately and stays latched without USB/DTR,
 // heartbeat, sensor readiness or the normal trial timeout. It does not arm.
 running();send("charge\n");assert(mode==CHARGE);
 assert(!motors[0].attached()&&!motors[1].attached()&&levels[D8]==LOW&&levels[D7]==LOW);
 assert(frames==0&&pulses[0]==0&&pulses[1]==0);
 assert(levels[PIN_CHARGING_CURRENT]==LOW);
 Wire1.regs[0x1e]=0;Serial.open=false;waitMs(61000);
 assert(mode==CHARGE&&frames==0&&!motors[0].attached()&&!motors[1].attached());
 Serial.open=true;send("state\nstatus\nhelp\nkeep\n");assert(mode==CHARGE);
 send("run\nstandalone\nshadow\n");assert(mode==CHARGE&&frames==0);
 send("off\n");checkOff();
 resetFixture();adcRaw=0;attitude=GravityFilter();send("charge\n");assert(mode==CHARGE);
 send("!\n");checkOff(); // Emergency stop remains available during charge.
 resetFixture();send("charge\n");send("arm\n");assert(mode==HOLD);
 waitMs(1100);send("standalone\n");assert(mode==STANDALONE);send("off\n");checkOff();
 std::cout<<"PASS: actual actor, 80-degree conversion, one-second neutral hold, 50 Hz target/PWM, shadow isolation, attach failures, battery/sensor/nonfinite/USB/heartbeat/deadline/session/input stops, nonblocking telemetry, clock rollover, standalone operation and latched no-PWM charging/rearming.\n";
}
'''
with tempfile.TemporaryDirectory() as folder:
    root=Path(folder)
    for path in ['firmware/policy_control','firmware/policy_shadow','firmware/servo_center','firmware/imu_bench','sim/recovery/results']:(root/path).mkdir(parents=True,exist_ok=True)
    (root/'Arduino.h').write_text(arduino);(root/'Adafruit_TinyUSB.h').write_text('')
    (root/'firmware/imu_bench/ImuBus.h').write_text(fixtures['BUS'])
    (root/'firmware/imu_bench/Lsm6ds3.h').write_bytes((HERE/'imu_bench/Lsm6ds3.h').read_bytes())
    (root/'firmware/servo_center/FineServo.h').write_text(servo)
    (root/'firmware/policy_shadow/MicrosecondClock.h').write_text(clock)
    for name in ['GravityFilter.h','MountCalibration.h']:(root/'firmware/policy_shadow'/name).write_bytes((HERE/'policy_shadow'/name).read_bytes())
    for name in ['policy_control.ino','ServoProfile.h']:(root/'firmware/policy_control'/name).write_bytes((HERE/'policy_control'/name).read_bytes())
    (root/'sim/recovery/results/policy_simulation_only.h').write_bytes((HERE.parent/'sim/recovery/results/policy_simulation_only.h').read_bytes())
    (root/'test.cpp').write_text(test)
    subprocess.run(['c++','-std=c++17','-O2','-I',str(root),str(root/'test.cpp'),'-o',str(root/'test')],check=True)
    capture=root/'capture.txt'
    subprocess.run([str(root/'test'),str(capture)],check=True)
    sys.path.insert(0,str(HERE.parent/'scripts'))
    from control import analyze
    from shadow import HostActor
    lines=capture.read_text().splitlines()
    header=next(line for line in lines if line.startswith('frame,t_us,mode,'))
    rows=list(csv.DictReader(io.StringIO(header+'\n'+'\n'.join(line[2:] for line in lines if line.startswith('D,')))))
    actor=HostActor()
    try:
        result=analyze(rows,actor,False)
        assert result['contract_checks']=='passed' and result['frames_logged']>=100
    finally:
        actor.close()
    print('PASS: real-sketch telemetry decodes through the supervisor; actor, target history, integration and PWM mapping agree.')
