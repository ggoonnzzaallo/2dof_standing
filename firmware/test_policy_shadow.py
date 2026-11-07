"""Exercise actual motor-disabled shadow sketch with fake USB/I2C/clock."""
from pathlib import Path
import ast
import re
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
tree=ast.parse((HERE/'test_imu_bench.py').read_text())
fixtures={n.targets[0].id:ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and isinstance(n.value,ast.Constant) and isinstance(n.value.value,str)}
arduino=re.sub(r'\bclockUs\b','fakeTimeUs',fixtures['ARDUINO'])
arduino=arduino.replace('void begin(int){}',"void begin(int){}\n void println(){output<<'\\n';fakeTimeUs+=serialCostUs;}")
CLOCK='''#pragma once
struct MicrosecondClock {void begin(){} uint32_t now()const{return uint32_t(fakeTimeUs);}};
'''
TEST=r'''
#include "firmware/policy_shadow/policy_shadow.ino"
#include <cassert>
#include <iostream>
void send(const char *s){Serial.send(s);loop();}
void fresh(uint64_t start=0){
 fakeTimeUs=start;Wire1.reset();Wire1.raw(5,4098);Serial.open=true;Serial.rx.clear();serialCostUs=0;
 imu=Lsm6ds3();attitude=GravityFilter();streaming=banner=discard=false;used=0;
 sampleAt=lastPoll=batteryAt=0;filterRejects=0;resetPolicy();setup();for(int i=0;i<20;++i){delay(5);loop();}assert(fresh());
}
int main(){
 fresh();assert(!streaming&&policyFrames==0);send("stream\n");assert(streaming&&policyFrames==0);
 delay(20);loop();assert(policyFrames==1);
 float previous[2]={action[0],action[1]},targets[2]={virtualTarget[0],virtualTarget[1]};
 for(int i=0;i<2;++i){assert(fabsf(action[i])<=1);assert(fabsf(targets[i]-.06f*action[i])<1e-6);}
 delay(20);loop();assert(policyFrames==2);
 for(int i=0;i<2;++i){assert(fabsf(observation[6+i]-targets[i]/JOINT_LIMIT_RAD)<1e-6);assert(observation[8+i]==previous[i]);}
 send("!\n");assert(!streaming&&policyFrames==0&&virtualTarget[0]==0&&virtualTarget[1]==0);
 send("stream\n");Serial.open=false;loop();assert(!streaming&&previousAction[0]==0);
 fresh();send("stream\n");Wire1.regs[0x1e]=0;delay(30);loop();assert(!streaming);
 fresh();send("stream\n");delay(30000);loop();assert(!streaming);
 fresh();send("stream\n");send("garbage\n");assert(!streaming);
 fresh();send("stream\n");serialCostUs=250;delay(20);loop();assert(streaming);serialCostUs=0;
 fresh((1ULL<<32)-180000);send("stream\n");for(int i=0;i<10;++i){delay(20);loop();assert(streaming);}
 assert(policyFrames==10);send("off\n");
 assert(levels[D8]==LOW&&levels[D7]==LOW); // Fake GPIO also rejects every HIGH write to these pins.
 std::cout<<"PASS: no automatic inference/PWM, exact virtual action history, stop/disconnect/stale/timeout handling, slow USB and 32-bit clock rollover.\n";
}
'''
# Avoid collision with the production fresh() status predicate.
TEST=TEST.replace('void fresh(uint64_t start=0)','void resetFixture(uint64_t start=0)').replace(' fresh();',' resetFixture();').replace(' fresh((1ULL',' resetFixture((1ULL')
with tempfile.TemporaryDirectory() as directory:
    root=Path(directory)
    shadow=root/'firmware/policy_shadow';shadow.mkdir(parents=True)
    imu=root/'firmware/imu_bench';imu.mkdir()
    actor=root/'sim/recovery/results';actor.mkdir(parents=True)
    (root/'Arduino.h').write_text(arduino);(root/'Adafruit_TinyUSB.h').write_text('')
    (imu/'ImuBus.h').write_text(fixtures['BUS'])
    (imu/'Lsm6ds3.h').write_bytes((HERE/'imu_bench/Lsm6ds3.h').read_bytes())
    for name in ('policy_shadow.ino','GravityFilter.h','MountCalibration.h'):
        (shadow/name).write_bytes((HERE/'policy_shadow'/name).read_bytes())
    (shadow/'MicrosecondClock.h').write_text(CLOCK)
    (actor/'policy_simulation_only.h').write_bytes((HERE.parent/'sim/recovery/results/policy_simulation_only.h').read_bytes())
    (root/'test.cpp').write_text(TEST)
    subprocess.run(['c++','-std=c++17','-O2','-I',str(root),str(root/'test.cpp'),'-o',str(root/'test')],check=True)
    subprocess.run([str(root/'test')],check=True)
