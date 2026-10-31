#pragma once
#include <Arduino.h>
#include <HardwarePWM.h>

constexpr uint8_t INVALID_SERVO = 255;

// Project-owned servo adapter. 16 MHz / 16 = 1 MHz: one tick per microsecond.
// 20,000 ticks retains the existing 50 Hz frame rate; no core/library patches.
class FineServo {
 public:
  bool attached() const { return pwm_ != nullptr; }
  uint8_t attach(uint8_t pin, int minimum, int maximum) {
    if (attached()) detach();
    for (int i=0; i<HWPWM_MODULE_NUM; ++i) {
      HardwarePWM* candidate=HwPWMx[i];
      const bool shared=candidate->isOwner(TOKEN);
      if (!shared && !candidate->takeOwnership(TOKEN)) continue;
      if (!candidate->addPin(pin)) {
        if (!shared) candidate->releaseOwnership(TOKEN);
        continue;
      }
      if (!shared) {
        candidate->setClockDiv(PWM_PRESCALER_PRESCALER_DIV_16);
        candidate->setMaxValue(20000);
      }
      pwm_=candidate; pin_=pin; minimum_=minimum; maximum_=maximum;
      return 0;
    }
    return INVALID_SERVO;
  }
  void writeMicroseconds(int us) {
    if (!pwm_) return;
    if (us<minimum_) us=minimum_;
    if (us>maximum_) us=maximum_;
    pwm_->writePin(pin_, uint16_t(us));
  }
  void detach() {
    if (!pwm_) return;
    pwm_->removePin(pin_);
    if (pwm_->usedChannelCount()==0) {
      pwm_->stop();
      pwm_->releaseOwnership(TOKEN);
    }
    digitalWrite(pin_,LOW);
    pwm_=nullptr;
  }
 private:
  static constexpr uint32_t TOKEN=0x524F4254;
  HardwarePWM* pwm_=nullptr;
  uint8_t pin_=0;
  int minimum_=1000, maximum_=2000;
};
