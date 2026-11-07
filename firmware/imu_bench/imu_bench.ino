// Sensor-only commissioning. D8/D7 remain LOW: no servo library or PWM.
#include <Arduino.h>
#include <Adafruit_TinyUSB.h>
#include <math.h>
#include <string.h>
#include "Lsm6ds3.h"

#ifndef TARGET_SEEED_XIAO_NRF52840_SENSE
#error "Use the classic XIAO nRF52840 Sense / non-mbed Seeed nRF52 core."
#endif

Lsm6ds3 imu;
bool streaming = false, banner = false, discard = false;
uint32_t streamAt = 0, pollAt = 0, reportAt = 0, batteryAt = 0;
uint16_t batteryMv = 0;
char command[24];
size_t used = 0;
const char *CSV_HEADER = "t_us,ax_g,ay_g,az_g,gx_rad_s,gy_rad_s,gz_rad_s,acc_norm_g,battery_mv,sample_seq,i2c_errors,saturated,age_us";

uint16_t readBatteryMv() {
  analogReference(AR_INTERNAL_3_0);
  analogReadResolution(12);
  analogSampleTime(40);
  (void)analogRead(PIN_VBAT);
  uint32_t sum = 0;
  for (uint8_t i=0; i<8; ++i) sum += analogRead(PIN_VBAT);
  return uint16_t((uint64_t(sum)*3000*1510)/(8ULL*4096*510));
}

void status() {
  Serial.println("ROBOT IMU BENCH 0.4");
  Serial.println("SENSOR_ONLY: D8/D7 LOW, no PWM; direct servo power is not disconnected.");
  Serial.print("IMU_READY: "); Serial.println(imu.ready ? 1 : 0);
  Serial.print("I2C_ADDRESS_DEC: "); Serial.println(imu.address);
  Serial.print("WHO_AM_I_DEC: "); Serial.println(imu.identity);
  Serial.println("IMU_CONFIG: sensor axes; 208 Hz; +/-8 g; +/-2000 deg/s; gyro output rad/s");
  Serial.print("I2C_ERRORS: "); Serial.println(imu.errors);
  Serial.print("I2C_LAST_ERROR: "); Serial.println(imu.bus.lastError);
  Serial.print("I2C_HW_ERROR: "); Serial.println(imu.bus.hardwareError);
  Serial.print("BATTERY_MV: "); Serial.println(batteryMv);
  Serial.println("Battery is an uncalibrated BAT-node estimate; USB does not establish net charging.");
  Serial.println("Commands: status, sample, stream (50 Hz, max 30 s), off, !, help");
}

bool fresh() { return imu.ready && imu.sequence && uint32_t(micros()-imu.sample.atUs) <= 100000; }

void report() {
  const ImuSample &s = imu.sample;
  Serial.print(s.atUs);
  for (uint8_t i=0; i<3; ++i) { Serial.print(','); Serial.print(s.accelG[i],6); }
  for (uint8_t i=0; i<3; ++i) { Serial.print(','); Serial.print(s.gyroRadS[i],6); }
  const float norm = sqrtf(s.accelG[0]*s.accelG[0]+s.accelG[1]*s.accelG[1]+s.accelG[2]*s.accelG[2]);
  Serial.print(','); Serial.print(norm,6);
  Serial.print(','); Serial.print(batteryMv);
  Serial.print(','); Serial.print(imu.sequence);
  Serial.print(','); Serial.print(imu.errors);
  Serial.print(','); Serial.print(s.saturated ? 1 : 0);
  Serial.print(','); Serial.println(uint32_t(micros()-s.atUs));
}

void handleCommand() {
  command[used] = 0;
  streaming = false;
  if (!strcmp(command,"stream") || !strcmp(command,"sample")) {
    if (!fresh()) { Serial.println("ERROR: IMU sample unavailable or stale."); return; }
    Serial.println(CSV_HEADER);
    report();
    if (!strcmp(command,"stream")) {
      streaming = true; streamAt = reportAt = millis();
    }
  } else if (!strcmp(command,"off")) Serial.println("OFF. Sensor stream stopped; no servo PWM.");
  else status();
}

void setup() {
  digitalWrite(D8,LOW); pinMode(D8,OUTPUT);
  digitalWrite(D7,LOW); pinMode(D7,OUTPUT);
  pinMode(D2,INPUT);
  digitalWrite(PIN_CHARGING_CURRENT,LOW); pinMode(PIN_CHARGING_CURRENT,OUTPUT);
  digitalWrite(VBAT_ENABLE,LOW); pinMode(VBAT_ENABLE,OUTPUT);
  Serial.begin(115200);
  imu.begin();
  batteryMv = readBatteryMv();
}

void loop() {
  const uint32_t now = millis();
  const uint32_t nowUs = micros();
  if (uint32_t(nowUs-pollAt) >= 1000) { pollAt = nowUs; imu.poll(); }
  if (uint32_t(now-batteryAt) >= 200) { batteryAt = now; batteryMv = readBatteryMv(); }
  if (!Serial) { streaming = false; banner = false; used = 0; discard = false; delay(1); return; }
  if (!banner) { status(); banner = true; }
  while (Serial.available()) {
    const char c = Serial.read();
    if (c == '!') { streaming = false; used = 0; discard = true; Serial.println("OFF. Sensor stream stopped."); }
    else if (c == '\n' || c == '\r') {
      if (!discard && used) handleCommand();
      used = 0; discard = false;
    } else if (!discard && used < sizeof(command)-1) command[used++] = c;
    else { streaming = false; used = 0; discard = true; }
  }
  if (streaming) {
    // A command above may start streaming after the loop-entry timestamp.
    // Re-read time to avoid unsigned underflow looking like a 30 s timeout.
    const uint32_t streamNow = millis();
    if (uint32_t(streamNow-streamAt) >= 30000) { streaming = false; Serial.println("OFF. 30 s sensor stream finished."); }
    else if (!fresh()) { streaming = false; Serial.println("ERROR: IMU sample stale; stream stopped."); }
    else if (uint32_t(streamNow-reportAt) >= 20) { reportAt = streamNow; report(); }
  }
  delay(1);
}
