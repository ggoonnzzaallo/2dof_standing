#pragma once
#include <Arduino.h>
#include <Wire.h>
#include <math.h>

// Classic XIAO Sense LSM6DS3TR-C; no external library or external I2C wires.
// Register/scaling reference: ST LSM6DS3TR-C datasheet, DocID030071 Rev 3.
struct ImuSample {
  uint32_t atUs = 0;
  float accelG[3] = {};
  float gyroRadS[3] = {};
  bool saturated = false;
};

class Lsm6ds3 {
 public:
  uint8_t address = 0, identity = 0;
  uint32_t errors = 0, sequence = 0;
  bool ready = false;
  ImuSample sample;

  bool begin() {
    ready = false;
    digitalWrite(PIN_LSM6DS3TR_C_POWER, HIGH);
    pinMode(PIN_LSM6DS3TR_C_POWER, OUTPUT);
    delay(20);
    Wire1.begin();
    Wire1.setClock(400000);
    const uint8_t candidates[] = {0x6a, 0x6b};
    for (uint8_t candidate : candidates) {
      address = candidate;
      if (read(0x0f, &identity, 1) && identity == 0x6a) break;
      address = 0;
    }
    if (!address || !write(0x12, 0x01)) return false; // Software reset.
    uint8_t control = 1;
    for (uint8_t i=0; i<50 && (control & 1); ++i) {
      delay(2);
      if (!read(0x12, &control, 1)) return false;
    }
    if (control & 1) return false;
    // BDU, increment, little endian; 208 Hz, +/-8 g and +/-2000 deg/s.
    if (!write(0x12, 0x44) || !write(0x10, 0x5c) || !write(0x11, 0x5c)) return false;
    const uint8_t regs[] = {0x12, 0x10, 0x11};
    const uint8_t expected[] = {0x44, 0x5c, 0x5c};
    for (uint8_t i=0; i<3; ++i) {
      if (!read(regs[i], &control, 1) || control != expected[i]) return false;
    }
    delay(40); // Gyro turn-on before collecting samples.
    ready = true;
    return true;
  }

  bool poll() {
    if (!ready) return false;
    uint8_t status;
    if (!read(0x1e, &status, 1) || (status & 3) != 3) return false;
    uint8_t bytes[12];
    if (!read(0x22, bytes, sizeof(bytes))) return false;
    ImuSample next;
    next.atUs = micros();
    for (uint8_t i=0; i<6; ++i) {
      // Explicit sign extension avoids implementation-dependent unsigned casts.
      const uint16_t bits = uint16_t(bytes[2*i]) | (uint16_t(bytes[2*i+1]) << 8);
      const int32_t raw = bits < 32768 ? int32_t(bits) : int32_t(bits)-65536;
      if (raw >= 32700 || raw <= -32700) next.saturated = true;
      if (i<3) next.gyroRadS[i] = raw*(0.070f*3.14159265358979323846f/180.f);
      else next.accelG[i-3] = raw*0.000244f;
    }
    sample = next;
    ++sequence;
    return true;
  }

 private:
  bool write(uint8_t reg, uint8_t value) {
    Wire1.beginTransmission(address);
    Wire1.write(reg); Wire1.write(value);
    if (Wire1.endTransmission() == 0) return true;
    ++errors;
    return false;
  }
  bool read(uint8_t reg, uint8_t *out, size_t count) {
    Wire1.beginTransmission(address);
    Wire1.write(reg);
    if (Wire1.endTransmission(false) != 0) { ++errors; return false; }
    if (Wire1.requestFrom(address, count) != count) {
      while (Wire1.available()) (void)Wire1.read();
      ++errors;
      return false;
    }
    for (size_t i=0; i<count; ++i) out[i] = Wire1.read();
    return true;
  }
};
