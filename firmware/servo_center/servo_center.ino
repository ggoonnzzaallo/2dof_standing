// Rev B: XIAO nRF52840 Sense + direct-battery PTK 7465 MG, supervised bench use.
// Select Seeed nRF52 Boards > Seeed XIAO nRF52840 Sense (non-mbed core).
// Boot is disarmed. Commands require a newline in the USB Serial Monitor.

#ifndef ROBOT_USE_POWER_SWITCH
#define ROBOT_USE_POWER_SWITCH 0  // Set to 1 only for the archived Pololu Rev A harness.
#endif

#include <Arduino.h>
#include <Adafruit_TinyUSB.h>
#include "FineServo.h"
#include <math.h>
#include <string.h>

#ifndef TARGET_SEEED_XIAO_NRF52840_SENSE
#error "Select Seeed XIAO nRF52840 Sense under Seeed nRF52 Boards (non-mbed)."
#endif

constexpr uint16_t CENTER_US = 1500;  // Nominal starting center; verify on hardware.
constexpr bool USE_SERVO_POWER_SWITCH = ROBOT_USE_POWER_SWITCH;
constexpr uint32_t POWER_TEST_MS = 3000;
constexpr uint32_t CENTER_HOLD_MS = 15000;
constexpr uint32_t JOG_STEP_MS = 1500;
constexpr uint16_t JOG_TARGETS_US[] = {1500, 1200, 1800, 1200, 1800, 1200, 1500};
constexpr size_t JOG_STEPS = sizeof(JOG_TARGETS_US) / sizeof(JOG_TARGETS_US[0]);
constexpr uint32_t JOG_HOLD_MS = JOG_STEP_MS * JOG_STEPS;
constexpr uint16_t SMALL_TARGETS_US[] = {1500, 1450, 1500, 1550, 1500};
constexpr size_t SMALL_STEPS = sizeof(SMALL_TARGETS_US) / sizeof(SMALL_TARGETS_US[0]);
constexpr uint32_t SMALL_HOLD_MS = JOG_STEP_MS * SMALL_STEPS;

// Continuous phase-offset waves, with gentle fade-in/out at neutral.
constexpr uint32_t DANCE_PERIOD_MS = 8000;
constexpr uint32_t LOOP_PERIOD_MS = 2500;
constexpr uint32_t DANCE_MOTION_MS = 24000;
constexpr uint32_t DANCE_RAMP_MS = 4000;
constexpr uint32_t DANCE_HOLD_MS = DANCE_MOTION_MS+1500;
constexpr uint32_t DANCE_UPDATE_MS = 20;
uint32_t lastDanceUpdateMs = 0;
uint32_t lastHeartbeatAt=0, lastBatteryAt=0, lastBatteryReportAt=0;
uint16_t batteryMv=0;
uint8_t lowBatteryCount=0;
constexpr uint32_t HEARTBEAT_MS=5000;

uint16_t readBatteryMv() {
  // Classic Sense divider: 1 MOhm above ADC, 510 kOhm to enabled ground.
  analogReference(AR_INTERNAL_3_0);
  analogReadResolution(12);
  analogSampleTime(40); // High-impedance divider needs long acquisition.
  (void)analogRead(PIN_VBAT);
  uint32_t sum=0;
  for (uint8_t i=0;i<8;++i) sum+=analogRead(PIN_VBAT);
  return uint16_t((uint64_t(sum)*3000*1510)/(8ULL*4096*510));
}

void reportBattery() {
  Serial.print("BATTERY_MV: "); Serial.println(batteryMv);
  Serial.println("Uncalibrated BAT-node estimate; USB connection does not prove net charging.");
}

bool batteryAllowsMotion() {
  batteryMv=readBatteryMv();
  if (batteryMv<3700 || batteryMv>4400) {
    Serial.println("REFUSED: battery below 3.7 V start threshold or reading invalid.");
    reportBattery();
    return false;
  }
  lowBatteryCount=0;
  lastBatteryAt=millis();
  return true;
}
FineServo activeServo;
FineServo secondServo;
uint8_t activeMode = 0;  // 0 off, 1 power, 2/3 center, 4/5 wide jog, 6/7 small jog.
uint8_t jogStep = 0;
uint32_t startedAt = 0;
uint32_t permittedMs = 0;
char command[24];
size_t commandLength = 0;
bool discardLine = false;

void motorOff() {
  // detach() must only be called when attached on the bundled nRF52 library.
  if (activeServo.attached()) activeServo.detach();
  if (secondServo.attached()) secondServo.detach();
  digitalWrite(D0, LOW);
  digitalWrite(D1, LOW);
  pinMode(D0, OUTPUT);
  pinMode(D1, OUTPUT);
  if (USE_SERVO_POWER_SWITCH) {
    digitalWrite(D2, LOW);
    pinMode(D2, OUTPUT);
  } else {
    pinMode(D2, INPUT);  // Unused in Rev B; no external wire.
  }
  activeMode = 0;
  permittedMs = 0;
  jogStep = 0;
}

void help() {
  Serial.println("ROBOT SERVO CENTER 0.9");
  Serial.println("OFF. No automatic movement. Support the arm and keep joints clear.");
  if (!USE_SERVO_POWER_SWITCH) {
    Serial.println("REV B DIRECT POWER: off/! stop PWM only; servo power stays live.");
    Serial.println("Full power-off requires battery AND USB disconnected.");
    Serial.println("Unplug both complete servo plugs for USB charging/programming.");
  }
  Serial.println("Connect the battery before any power/centering command.");
  Serial.println(USE_SERVO_POWER_SWITCH ? "power  : Rev A rail enabled for 3 seconds, no pulses"
                                        : "power  : unavailable; Rev B has no power switch");
  Serial.println("battery : read BAT voltage estimate, millivolts");
  Serial.println("dance-loop : continuous FAST waves; keep heartbeat every 2 seconds; off/! stops");
  Serial.println("dance  : BOTH joints, smooth 1100-1900 us, center then stop after 25.5 seconds");
  Serial.println("lower  : lower servo D0 at 1500 us for 15 seconds");
  Serial.println("upper  : upper servo D1 at 1500 us for 15 seconds");
  Serial.println("lower-jog : HORNS OFF ONLY, D0 1200-1800 us, off in 10.5 seconds");
  Serial.println("upper-jog : HORNS OFF ONLY, D1 1200-1800 us, off in 10.5 seconds");
  Serial.println("lower-small : D0 1500/1450/1500/1550/1500 us, off in 7.5 seconds");
  Serial.println("upper-small : D1 1500/1450/1500/1550/1500 us, off in 7.5 seconds");
  Serial.println(USE_SERVO_POWER_SWITCH ? "off    : stop PWM and request Rev A rail off"
                                        : "off    : stop PWM ONLY; direct power remains connected");
  Serial.println("!      : immediate off, no newline needed");
  Serial.println("help   : stop and show these commands");
  if (USE_SERVO_POWER_SWITCH) Serial.println("Rev A Pololu slide must stay OFF for MCU control.");
}

void explainStop() {
  if (!USE_SERVO_POWER_SWITCH) {
    Serial.println("PWM stopped only; direct servo power remains connected.");
  }
}

void beginTest(uint8_t mode) {
  motorOff();
  if (mode == 1 && !USE_SERVO_POWER_SWITCH) {
    Serial.println("No electronic power switch: power command has no effect. PWM remains stopped.");
    return;
  }
  if (!batteryAllowsMotion()) return;
  // Rev A enables power first; Rev B's direct supply is already live.
  if (USE_SERVO_POWER_SWITCH) digitalWrite(D2, HIGH);
  startedAt = millis();
  activeMode = mode;
  permittedMs = mode == 1 ? POWER_TEST_MS :
                (mode >= 6 ? SMALL_HOLD_MS : (mode >= 4 ? JOG_HOLD_MS : CENTER_HOLD_MS));
  if (mode == 1) {
    Serial.println("POWER ONLY: measure VOUT to GND now; off in 3 seconds.");
    return;
  }
  delay(20);
  const uint8_t pin = (mode == 2 || mode == 4 || mode == 6) ? D0 : D1;
  if (activeServo.attach(pin, 1000, 2000) == INVALID_SERVO) {
    motorOff();
    Serial.println("ERROR: could not start PWM; outputs stopped.");
    explainStop();
    return;
  }
  activeServo.writeMicroseconds(CENTER_US);
  if (mode >= 6) {
    Serial.println(mode == 6 ? "LOWER SMALL: 1450-1550 us, center, off in 7.5 seconds."
                            : "UPPER SMALL: 1450-1550 us, center, off in 7.5 seconds.");
    return;
  }
  if (mode >= 4) {
    Serial.println(mode == 4 ? "LOWER JOG: 1200-1800 us, center, off in 10.5 seconds."
                            : "UPPER JOG: 1200-1800 us, center, off in 10.5 seconds.");
    return;
  }
  Serial.println(mode == 2 ? "LOWER: 1500 us, off in 15 seconds."
                          : "UPPER: 1500 us, off in 15 seconds.");
}

void beginDance(bool continuous=false) {
  motorOff();
  if (!batteryAllowsMotion()) return;
  if (USE_SERVO_POWER_SWITCH) digitalWrite(D2, HIGH);
  if (activeServo.attach(D0,1000,2000)==INVALID_SERVO ||
      secondServo.attach(D1,1000,2000)==INVALID_SERVO) {
    motorOff();
    Serial.println("ERROR: could not start both PWM outputs.");
    return;
  }
  activeServo.writeMicroseconds(CENTER_US);
  secondServo.writeMicroseconds(CENTER_US);
  startedAt=millis();
  permittedMs=DANCE_HOLD_MS;
  lastDanceUpdateMs=0;
  activeMode=continuous ? 9 : 8;
  lastHeartbeatAt=millis();
  if (continuous) {
    Serial.println("DANCE LOOP: 2.5-second cycles, 1100-1900 us, battery guard and heartbeat enabled.");
    return;
  }
  Serial.println("DANCE: BOTH joints 1100-1900 us, neutral then PWM off in 25.5 seconds.");
}

void updateDance(uint32_t elapsed) {
  if (elapsed-lastDanceUpdateMs<DANCE_UPDATE_MS) return;
  // Anchor targets to the fixed frame grid; do not accumulate loop-delay drift.
  lastDanceUpdateMs=elapsed-(elapsed%DANCE_UPDATE_MS);
  elapsed=lastDanceUpdateMs;
  const bool continuous=activeMode==9;
  if (!continuous && elapsed>=DANCE_MOTION_MS) {
    activeServo.writeMicroseconds(CENTER_US);
    secondServo.writeMicroseconds(CENTER_US);
    return;
  }
  const uint32_t rampTime=continuous ? elapsed :
    (elapsed<DANCE_MOTION_MS-elapsed ? elapsed : DANCE_MOTION_MS-elapsed);
  const float t=rampTime<DANCE_RAMP_MS ? float(rampTime)/DANCE_RAMP_MS : 1.0f;
  const float envelope=t*t*t*(10.0f+t*(-15.0f+6.0f*t));
  constexpr float PI_F=3.14159265358979323846f;
  const uint32_t period=continuous ? LOOP_PERIOD_MS : DANCE_PERIOD_MS;
  const float phase=2.0f*PI_F*float(elapsed%period)/period;
  activeServo.writeMicroseconds(CENTER_US+int(lroundf(400.0f*envelope*sinf(phase))));
  secondServo.writeMicroseconds(CENTER_US+int(lroundf(400.0f*envelope*cosf(phase))));
}

void executeCommand() {
  command[commandLength] = '\0';
  if (strcmp(command, "battery")==0) {
    if (!activeMode) batteryMv=readBatteryMv();
    reportBattery();
  }
  else if (strcmp(command, "keep")==0) {
    if (activeMode==9) lastHeartbeatAt=millis();
  }
  else if (strcmp(command, "dance-loop")==0) beginDance(true);
  else if (strcmp(command, "dance") == 0) beginDance();
  else if (strcmp(command, "power") == 0) beginTest(1);
  else if (strcmp(command, "lower") == 0) beginTest(2);
  else if (strcmp(command, "upper") == 0) beginTest(3);
  else if (strcmp(command, "lower-jog") == 0) beginTest(4);
  else if (strcmp(command, "upper-jog") == 0) beginTest(5);
  else if (strcmp(command, "lower-small") == 0) beginTest(6);
  else if (strcmp(command, "upper-small") == 0) beginTest(7);
  else {
    motorOff();
    if (strcmp(command, "help") == 0) help();
    else if (strcmp(command, "off") == 0) {
      Serial.println("OFF.");
      explainStop();
    } else {
      Serial.println("Unknown command; PWM stopped. Send help.");
      explainStop();
    }
  }
  commandLength = 0;
}

void setup() {
  // Stop both signals immediately; Rev A also disables its power switch.
  motorOff();
  // Use the board-core pin mappings, not Arduino pin 13 (which is an LED).
  digitalWrite(VBAT_ENABLE, LOW);
  pinMode(VBAT_ENABLE, OUTPUT);
  digitalWrite(PIN_CHARGING_CURRENT, LOW);
  pinMode(PIN_CHARGING_CURRENT, OUTPUT);  // Approximately 100 mA USB charging.
  Serial.begin(115200);
}

void loop() {
  static bool hadSerial = false;
  const bool serialOpen = bool(Serial);
  if (!serialOpen) {
    motorOff();
    commandLength = 0;
    discardLine = false;
    hadSerial = false;
    delay(2);
    return;
  }
  if (!hadSerial) {
    motorOff();
    hadSerial = true;
    help();
  }

  if (activeMode && activeMode!=9 && uint32_t(millis() - startedAt) >= permittedMs) {
    motorOff();
    Serial.println("OFF: test timer expired.");
    explainStop();
  }

  if (activeMode && uint32_t(millis()-lastBatteryAt)>=100) {
    lastBatteryAt=millis();
    batteryMv=readBatteryMv();
    if (batteryMv<3600) ++lowBatteryCount; else lowBatteryCount=0;
    if (batteryMv<3400 || batteryMv>4400 || lowBatteryCount>=2) {
      motorOff();
      Serial.println("STOP: LOW BATTERY or invalid ADC reading. Unplug battery AND USB.");
      reportBattery();
      explainStop();
    }
    if (uint32_t(millis()-lastBatteryReportAt)>=1000) {
      lastBatteryReportAt=millis();
      Serial.print("BATTERY_MV: "); Serial.println(batteryMv);
    }
  }
  if (activeMode==9 && uint32_t(millis()-lastHeartbeatAt)>=HEARTBEAT_MS) {
    motorOff();
    Serial.println("OFF: host heartbeat expired.");
    explainStop();
  }
  if (activeMode == 8 || activeMode == 9) updateDance(uint32_t(millis()-startedAt));
  else if (activeMode >= 4) {
    const uint32_t step = uint32_t(millis() - startedAt) / JOG_STEP_MS;
    const size_t steps = activeMode >= 6 ? SMALL_STEPS : JOG_STEPS;
    if (step < steps && step != jogStep) {
      jogStep = uint8_t(step);
      activeServo.writeMicroseconds(activeMode >= 6 ? SMALL_TARGETS_US[step] : JOG_TARGETS_US[step]);
    }
  }

  // Bound input work so a serial flood cannot starve the test timeout.
  for (uint8_t n = 0; n < 64 && Serial.available(); ++n) {
    const char c = char(Serial.read());
    if (c == '!') {
      motorOff();
      commandLength = 0;
      discardLine = true;  // Discard any queued command tail until newline.
      Serial.println("OFF: emergency stop. Send a newline before another command.");
      explainStop();
      continue;
    }
    if (c == '\r' || c == '\n') {
      if (discardLine) {
        discardLine = false;
        commandLength = 0;
      } else if (commandLength) executeCommand();
    } else if (!discardLine) {
      if (commandLength < sizeof(command) - 1) command[commandLength++] = c;
      else {
        motorOff();
        commandLength = 0;
        discardLine = true;
        Serial.println("OFF: input too long; line discarded.");
        explainStop();
      }
    }
  }
}
