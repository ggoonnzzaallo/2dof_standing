#pragma once
#include <math.h>
#include <stdint.h>

// The IMU measures the base, not either joint. A fixed acceleration reference
// catches gradual tilts as well as bumps; gyro also catches rotation about gravity.
// Three consecutive samples reject isolated noise spikes. All units are g/rad/s.
class InactivityGuard {
 public:
  static constexpr uint32_t TIMEOUT_MS = 60000;
  static constexpr float ACCEL_DELTA_G = .04f;
  static constexpr float GYRO_RAD_S = .08f;
  bool locked = false; // Only MCU reset clears this; begin()/stop/charge never do.
  uint32_t lastMotionMs = 0;

  void begin(uint32_t now, const float accel[3]) {
    if (locked) return;
    lastMotionMs = now; movingSamples = 0;
    for (int i=0;i<3;++i) reference[i] = accel[i];
  }
  void observe(uint32_t now, const float accel[3], const float gyro[3]) {
    if (locked) return;
    float delta2=0, speed2=0;
    for (int i=0;i<3;++i) {
      if (!isfinite(accel[i]) || !isfinite(gyro[i])) return;
      const float d=accel[i]-reference[i]; delta2+=d*d; speed2+=gyro[i]*gyro[i];
    }
    if (delta2>=ACCEL_DELTA_G*ACCEL_DELTA_G || speed2>=GYRO_RAD_S*GYRO_RAD_S) {
      if (++movingSamples>=3) {
        lastMotionMs=now; movingSamples=0;
        for (int i=0;i<3;++i) reference[i]=accel[i];
      }
    } else movingSamples=0;
  }
  bool expired(uint32_t now) {
    if (uint32_t(now-lastMotionMs)>=TIMEOUT_MS) locked=true;
    return locked;
  }
 private:
  float reference[3]={};
  uint8_t movingSamples=0;
};
