// Arithmetic-only probe for the simulation-trained actor. No IMU or servo PWM.
// Build separately; the normal upload command still uploads servo_center.
#include <Arduino.h>
#include <Adafruit_TinyUSB.h>
#include <string.h>
#include "../../sim/recovery/results/policy_simulation_only.h"

#ifndef TARGET_SEEED_XIAO_NRF52840_SENSE
#error "Select the classic XIAO nRF52840 Sense / non-mbed Seeed nRF52 core."
#endif

void runProbe() {
  float observation[10] = {0,0,-1,0,0,0,0,0,0,0};
  float action[2];
  robot_policy(observation, action);
  Serial.print("UPRIGHT_ACTION: ");Serial.print(action[0],7);Serial.print(' ');Serial.println(action[1],7);
  uint32_t totalUs = 0, maxUs = 0;
  volatile float checksum = 0;
  for (uint16_t i=0; i<200; ++i) {
    // Vary an input so the compiler cannot replace inference with one constant.
    observation[8] = float(int(i%17)-8)/8.0f;
    const uint32_t start = micros();
    robot_policy(observation, action);
    const uint32_t elapsed = micros()-start;
    totalUs += elapsed;
    if (elapsed>maxUs) maxUs = elapsed;
    checksum += action[i&1];
    if ((i&15)==0) yield();
  }
  Serial.print("INFERENCE_AVG_US: ");Serial.println(float(totalUs)/200.0f,2);
  Serial.print("INFERENCE_MAX_US: ");Serial.println(maxUs);
  Serial.print("CHECKSUM: ");Serial.println(checksum,6);
  Serial.println("PROBE_DONE. No servo pulses generated.");
}

void setup() {
  digitalWrite(D8,LOW);pinMode(D8,OUTPUT);
  digitalWrite(D7,LOW);pinMode(D7,OUTPUT);
  // Preserve the bench firmware's documented charger configuration.
  digitalWrite(PIN_CHARGING_CURRENT,LOW);pinMode(PIN_CHARGING_CURRENT,OUTPUT);
  digitalWrite(VBAT_ENABLE,LOW);pinMode(VBAT_ENABLE,OUTPUT);
  Serial.begin(115200);
}

void loop() {
  static bool banner = false;
  static char command[16];
  static uint8_t used = 0;
  if (Serial && !banner) {
    Serial.println("POLICY_PROBE_SIM_ONLY: D8/D7 held LOW; no PWM. Send probe or help.");
    banner = true;
  }
  if (!Serial) banner = false;
  while (Serial.available()) {
    const char c = Serial.read();
    if (c=='\n' || c=='\r') {
      command[used]=0;
      if (strcmp(command,"probe")==0) runProbe();
      else if (used) Serial.println("Commands: probe, help. Arithmetic only; no servo control.");
      used = 0;
    } else if (used<sizeof(command)-1) command[used++]=c;
    else used=0;
  }
  delay(1);
}
