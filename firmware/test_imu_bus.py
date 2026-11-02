"""Check the actual TWIM transport's deadlines with fake peripheral events.

This tests control flow, not electrical timing or the Nordic DMA hardware.
"""
from pathlib import Path
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
ARDUINO = r'''
#pragma once
#include <cstdint>
#include <cstddef>
struct Dma {uint32_t PTR=0,MAXCNT=0,AMOUNT=0;};
struct Pins {uint32_t SDA=0,SCL=0;};
struct Twim {
 uint32_t ENABLE=0,INTENCLR=0,FREQUENCY=0,SHORTS=0,ERRORSRC=0,ADDRESS=0;
 uint32_t EVENTS_STOPPED=0,EVENTS_ERROR=0,EVENTS_LASTTX=0,EVENTS_LASTRX=0;
 uint32_t TASKS_STARTTX=0,TASKS_RESUME=0,TASKS_STOP=0;
 Dma TXD,RXD;Pins PSEL;
};
inline Twim fake;
inline Twim *NRF_TWIM1=&fake;
inline uint64_t clockUs=0;
inline int mode=0; // 0 success, 1 NACK, 2 missing all events, 3 short DMA.
inline uint32_t micros(){
 ++clockUs;
 if(fake.ENABLE&&fake.TASKS_STARTTX){
  if(mode==0||mode==3){
   fake.EVENTS_STOPPED=1;fake.TXD.AMOUNT=fake.TXD.MAXCNT;
   fake.RXD.AMOUNT=mode==3?0:fake.RXD.MAXCNT;
  }else if(mode==1)fake.EVENTS_ERROR=1;
 }
 return uint32_t(clockUs);
}
inline uint32_t g_ADigitalPinMap[33]={};
constexpr int PIN_WIRE1_SDA=17,PIN_WIRE1_SCL=16;
constexpr int SPIM1_SPIS1_TWIM1_TWIS1_SPI1_TWI1_IRQn=1;
constexpr int TWIM_FREQUENCY_FREQUENCY_K400=400000,TWIM_ENABLE_ENABLE_Enabled=6;
constexpr int TWIM_SHORTS_LASTTX_STARTRX_Msk=128,TWIM_SHORTS_LASTRX_STOP_Msk=4096,TWIM_SHORTS_LASTTX_STOP_Msk=512;
inline void NVIC_DisableIRQ(int){}
'''
GPIO = r'''
#pragma once
constexpr int NRF_GPIO_PIN_DIR_INPUT=0,NRF_GPIO_PIN_INPUT_CONNECT=0,NRF_GPIO_PIN_PULLUP=1;
constexpr int NRF_GPIO_PIN_S0D1=6,NRF_GPIO_PIN_NOSENSE=0;
inline void nrf_gpio_cfg(uint32_t,int,int,int,int,int){}
'''
TEST = r'''
#include "ImuBus.h"
#include <cassert>
#include <iostream>
int main(){
 ImuBus bus;bus.begin();uint8_t bytes[12]={};
 assert(bus.read(0x6a,0x22,bytes,12));
 assert(fake.ADDRESS==0x6a&&fake.TXD.MAXCNT==1&&fake.RXD.MAXCNT==12&&fake.ENABLE==0);
 assert(fake.SHORTS==(TWIM_SHORTS_LASTTX_STARTRX_Msk|TWIM_SHORTS_LASTRX_STOP_Msk));
 assert(bus.write(0x6a,0x12,0x44));assert(fake.TXD.MAXCNT==2&&fake.ENABLE==0);
 assert(!bus.read(0x6a,0x22,bytes,0));assert(!bus.read(0x6a,0x22,bytes,256));
 mode=3;assert(!bus.read(0x6a,0x22,bytes,12));
 for(int failure:{1,2}){
  for(uint64_t start:{0ULL,0xfffffff0ULL}){
   clockUs=start;mode=failure;
   assert(!bus.read(0x6a,0x22,bytes,12));
   assert(clockUs-start<=3510&&fake.ENABLE==0&&fake.SHORTS==0);
   mode=0;assert(bus.read(0x6a,0x22,bytes,12)); // A failed transfer does not poison all future reads.
  }
 }
 std::cout<<"PASS: repeated-start/DMA setup, short transfers, bounded NACK/missing-event waits, timer rollover and subsequent transaction recovery.\n";
}
'''
with tempfile.TemporaryDirectory() as directory:
    folder=Path(directory)
    (folder/'Arduino.h').write_text(ARDUINO)
    (folder/'nrf_gpio.h').write_text(GPIO)
    (folder/'ImuBus.h').write_bytes((HERE/'imu_bench/ImuBus.h').read_bytes())
    (folder/'test.cpp').write_text(TEST)
    subprocess.run(['c++','-std=c++17','-I',str(folder),str(folder/'test.cpp'),'-o',str(folder/'test')],check=True)
    subprocess.run([str(folder/'test')],check=True)
