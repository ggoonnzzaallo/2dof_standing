// XIAO nRF52840 Sense + Pololu 2810 + PTK 7465 MG, supervised bench use.
// Select Seeed nRF52 Boards > Seeed XIAO nRF52840 Sense (non-mbed core).
// Boot is disarmed. Commands require a newline in the USB Serial Monitor.

#include <Arduino.h>
#include <Adafruit_TinyUSB.h>
#include <Servo.h>
#include <string.h>

#ifndef TARGET_SEEED_XIAO_NRF52840_SENSE
#error "Select Seeed XIAO nRF52840 Sense under Seeed nRF52 Boards (non-mbed)."
#endif

constexpr uint16_t CENTER_US = 1500;  // Nominal starting center; verify on hardware.
constexpr uint32_t POWER_TEST_MS = 3000;
constexpr uint32_t CENTER_HOLD_MS = 15000;
constexpr uint32_t JOG_STEP_MS = 1500;
constexpr uint16_t JOG_TARGETS_US[] = {1500, 1200, 1800, 1200, 1800, 1200, 1500};
constexpr size_t JOG_STEPS = sizeof(JOG_TARGETS_US) / sizeof(JOG_TARGETS_US[0]);
constexpr uint32_t JOG_HOLD_MS = JOG_STEP_MS * JOG_STEPS;

Servo activeServo;
uint8_t activeMode = 0;  // 0 off, 1 power-only, 2/3 center lower/upper, 4/5 jog.
uint8_t jogStep = 0;
uint32_t startedAt = 0;
uint32_t permittedMs = 0;
char command[24];
size_t commandLength = 0;
bool discardLine = false;

void motorOff() {
  // detach() must only be called when attached on the bundled nRF52 library.
  if (activeServo.attached()) activeServo.detach();
  digitalWrite(D0, LOW);
  digitalWrite(D1, LOW);
  pinMode(D0, OUTPUT);
  pinMode(D1, OUTPUT);
  digitalWrite(D2, LOW);
  pinMode(D2, OUTPUT);
  activeMode = 0;
  permittedMs = 0;
  jogStep = 0;
}

void help() {
  Serial.println("ROBOT SERVO CENTER 0.2");
  Serial.println("OFF. No automatic movement. Keep horns/printed moving links off.");
  Serial.println("Connect the battery before any power/centering command.");
  Serial.println("power  : VOUT enabled for 3 seconds, no servo pulses");
  Serial.println("lower  : lower servo D0 at 1500 us for 15 seconds");
  Serial.println("upper  : upper servo D1 at 1500 us for 15 seconds");
  Serial.println("lower-jog : D0 back/forth 1200-1800 us, center, off in 10.5 seconds");
  Serial.println("upper-jog : D1 back/forth 1200-1800 us, center, off in 10.5 seconds");
  Serial.println("off    : stop PWM and disable the servo rail");
  Serial.println("!      : immediate off, no newline needed");
  Serial.println("help   : stop and show these commands");
  Serial.println("Pololu slide must stay OFF. Disconnect the pack for true power-off.");
}

void beginTest(uint8_t mode) {
  motorOff();
  // Power first; signal pins remain LOW until the selected PWM is attached.
  digitalWrite(D2, HIGH);
  startedAt = millis();
  activeMode = mode;
  permittedMs = mode == 1 ? POWER_TEST_MS : (mode >= 4 ? JOG_HOLD_MS : CENTER_HOLD_MS);
  if (mode == 1) {
    Serial.println("POWER ONLY: measure VOUT to GND now; off in 3 seconds.");
    return;
  }
  delay(20);
  const uint8_t pin = (mode == 2 || mode == 4) ? D0 : D1;
  if (activeServo.attach(pin, 1000, 2000) == INVALID_SERVO) {
    motorOff();
    Serial.println("ERROR: could not start PWM; rail disabled.");
    return;
  }
  activeServo.writeMicroseconds(CENTER_US);
  if (mode >= 4) {
    Serial.println(mode == 4 ? "LOWER JOG: 1200-1800 us, center, off in 10.5 seconds."
                            : "UPPER JOG: 1200-1800 us, center, off in 10.5 seconds.");
    return;
  }
  Serial.println(mode == 2 ? "LOWER: 1500 us, off in 15 seconds."
                          : "UPPER: 1500 us, off in 15 seconds.");
}

void executeCommand() {
  command[commandLength] = '\0';
  if (strcmp(command, "power") == 0) beginTest(1);
  else if (strcmp(command, "lower") == 0) beginTest(2);
  else if (strcmp(command, "upper") == 0) beginTest(3);
  else if (strcmp(command, "lower-jog") == 0) beginTest(4);
  else if (strcmp(command, "upper-jog") == 0) beginTest(5);
  else {
    motorOff();
    if (strcmp(command, "help") == 0) help();
    else if (strcmp(command, "off") == 0) Serial.println("OFF.");
    else Serial.println("Unknown command; rail disabled. Send help.");
  }
  commandLength = 0;
}

void setup() {
  // First operations in the sketch leave motor power and both signals LOW.
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

  if (activeMode && uint32_t(millis() - startedAt) >= permittedMs) {
    motorOff();
    Serial.println("OFF: test timer expired.");
  }

  if (activeMode >= 4) {
    const uint32_t step = uint32_t(millis() - startedAt) / JOG_STEP_MS;
    if (step < JOG_STEPS && step != jogStep) {
      jogStep = uint8_t(step);
      activeServo.writeMicroseconds(JOG_TARGETS_US[step]);
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
      }
    }
  }
}
