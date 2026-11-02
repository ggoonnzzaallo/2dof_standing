#pragma once
#include <math.h>
#include <stdint.h>

// Deployment profile authorized 2026-11-02: retain trained +/-80 degrees.
// Visual reference points were measured only at 0 and +/-45 degrees.
// Outside that interval this is an explicitly authorized linear extrapolation,
// NOT a measurement of physical travel, angle precision or collision clearance.
constexpr float CONTROL_LIMIT_RAD = 1.3962634016f;
constexpr float PULSE_US_PER_RAD = -509.29581789406507f;
inline bool controlPulse(float angle, uint16_t& pulse) {
  if (!isfinite(angle) || fabsf(angle) > CONTROL_LIMIT_RAD + 1e-6f) return false;
  const long value = lroundf(1500.f + PULSE_US_PER_RAD * angle);
  if (value < 789 || value > 2211) return false;
  pulse = uint16_t(value);
  return true;
}
