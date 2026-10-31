"""Supervised continuous fast dance. Ctrl+C stops PWM; direct battery power remains live."""
import argparse
import os
from pathlib import Path
import re
import signal
import time
import serial
import robot

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--port')
args=parser.parse_args()
port=robot.find_port(args.port)
robot.BUILD.parent.mkdir(parents=True,exist_ok=True)
pidfile=robot.BUILD.parent/'dance.pid'
logfile=robot.BUILD.parent/'dance.log'
if pidfile.exists():
    try:
        os.kill(int(pidfile.read_text()),0)
    except (ProcessLookupError,ValueError):
        pidfile.unlink(missing_ok=True)
    else:
        raise SystemExit('A dance host is already running; stop it before opening another.')
pidfile.write_text(str(os.getpid()))
running=True

def stop(signum,frame):
    global running
    running=False

signal.signal(signal.SIGTERM,stop)
signal.signal(signal.SIGINT,stop)
s=None
with logfile.open('a',buffering=1) as log:
    def emit(line):
        print(line,flush=True)
        log.write(time.strftime('%Y-%m-%d %H:%M:%S ')+line+'\n')
    try:
        s=serial.Serial(port,115200,timeout=.2,write_timeout=1)
        time.sleep(1)
        s.write(b'help\noff\nbattery\n');s.flush();time.sleep(.4)
        initial=s.read(8192).decode(errors='replace')
        if 'ROBOT SERVO CENTER 0.9' not in initial or 'OFF.' not in initial.splitlines():
            raise RuntimeError('Expected version/disarmed acknowledgement missing: '+initial)
        volts=re.findall(r'BATTERY_MV: (\d+)',initial)
        if not volts or not 3700<=int(volts[-1])<=4400:
            raise RuntimeError('Battery estimate not acceptable for starting: '+initial)
        emit('Initial BAT estimate: '+volts[-1]+' mV (uncalibrated, USB connected).')
        if running:
            s.write(b'dance-loop\n');s.flush()
        next_keep=time.monotonic()
        buffer=''
        while running:
            if time.monotonic()>=next_keep:
                s.write(b'keep\n');s.flush();next_keep=time.monotonic()+2
            buffer+=s.read(2048).decode(errors='replace')
            while '\n' in buffer:
                line,buffer=buffer.split('\n',1)
                line=line.strip()
                if not line:continue
                emit(line)
                if line.startswith(('STOP:','OFF:','OFF.','REFUSED:','ROBOT SERVO')):
                    running=False
        emit('Dance host stopping; sending explicit PWM off.')
    finally:
        try:
            if s:
                try:
                    s.write(b'!\noff\n');s.flush();time.sleep(.2)
                    emit(s.read(2048).decode(errors='replace').strip())
                finally:s.close()
        finally:
            pidfile.unlink(missing_ok=True)
