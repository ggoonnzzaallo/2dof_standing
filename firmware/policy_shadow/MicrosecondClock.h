#pragma once
#include <Arduino.h>

// Exclusive, polled TIMER4 ownership. No DWT changes: core micros() retains its
// normal RTOS behavior. 1 MHz, full 32-bit counter (wraps after ~71.6 minutes).
class MicrosecondClock {
 public:
  void begin(){
    NVIC_DisableIRQ(TIMER4_IRQn);
    NRF_TIMER4->TASKS_STOP=1;
    NRF_TIMER4->INTENCLR=0xffffffff;
    NRF_TIMER4->SHORTS=0;
    NRF_TIMER4->MODE=TIMER_MODE_MODE_Timer;
    NRF_TIMER4->BITMODE=TIMER_BITMODE_BITMODE_32Bit;
    NRF_TIMER4->PRESCALER=4; // Nordic timer base clock is 16 MHz.
    NRF_TIMER4->TASKS_CLEAR=1;
    NRF_TIMER4->TASKS_START=1;
  }
  uint32_t now()const {NRF_TIMER4->TASKS_CAPTURE[0]=1;return NRF_TIMER4->CC[0];}
};
