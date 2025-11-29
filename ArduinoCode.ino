#include <Arduino.h>
#include <ESP32Servo.h>

// =========================
// Configuration
// =========================

const int SERVO_PINS_FIRST_4[4] = {4, 5, 6, 7};    // D4, D5, D6, D7
const int SERVO_PINS_LAST_4[4]  = {8, 9, 10, 11};  // D8, D9, D10, D11

Servo servos[8];

const int ANGLE_CLOSED = 0;
const int ANGLE_OPEN   = 90;

// Optional: define min/max pulse for your servos (microseconds)
const int SERVO_MIN_US = 500;   // adjust if needed
const int SERVO_MAX_US = 2400;  // adjust if needed

// =========================
// Helpers
// =========================

void attachServos() {
  // Attach first 4 servos
  for (int i = 0; i < 4; i++) {
    servos[i].attach(SERVO_PINS_FIRST_4[i], SERVO_MIN_US, SERVO_MAX_US);
  }
  // Attach last 4 servos
  for (int i = 0; i < 4; i++) {
    servos[4 + i].attach(SERVO_PINS_LAST_4[i], SERVO_MIN_US, SERVO_MAX_US);
  }

  // Initialize all servos to closed
  for (int i = 0; i < 8; i++) {
    servos[i].write(ANGLE_CLOSED);
  }
  delay(500);
}

void dropFirstFour() {
  void dropFirstFour() {
  // Open first 2 servos
  servos[0].write(ANGLE_OPEN);
  servos[1].write(ANGLE_OPEN);

  // Wait 200 milliseconds
  delay(65);

  // Open 3rd and 4th servos
  servos[2].write(ANGLE_OPEN);
  servos[3].write(ANGLE_OPEN);

  // Wait 5 seconds with all 4 open
  delay(5000);

  // Close all 4 servos
  for (int i = 0; i < 4; i++) {
    servos[i].write(ANGLE_CLOSED);
  }

  delay(500); // small pause after closing
}
}

void sortLastFour(int pattern[4]) {
  // pattern[i] = 1 for good (open), 0 for bad (closed)
  for (int i = 0; i < 4; i++) {
    int idx = 4 + i;
    if (pattern[i] == 1) {
      servos[idx].write(ANGLE_OPEN);
    } else {
      servos[idx].write(ANGLE_CLOSED);
    }
  }
  delay(5000);
  for (int i = 0; i < 4; i++) {
    servos[4 + i].write(ANGLE_CLOSED);
  }
  delay(500);
}

// =========================
// Serial command parsing
// =========================

String inputLine = "";

void processLine(String line) {
  line.trim();
  if (line.length() == 0) return;

  Serial.print("Received: ");
  Serial.println(line);

  if (line == "D") {
    dropFirstFour();
    return;
  }

  if (line.startsWith("S")) {
    // expected: S a b c d  (each a/b/c/d is 0 or 1)
    int pattern[4] = {0, 0, 0, 0};
    int idx = 0;

    char buf[32];
    line.toCharArray(buf, sizeof(buf));
    char *token = strtok(buf, " ");
    // first token is "S"
    token = strtok(NULL, " ");
    while (token != NULL && idx < 4) {
      pattern[idx] = atoi(token);
      idx++;
      token = strtok(NULL, " ");
    }

    sortLastFour(pattern);
    return;
  }

  Serial.println("Unknown command");
}

// =========================
// Arduino setup/loop
// =========================

void setup() {
  Serial.begin(115200);
  attachServos();
  Serial.println("ESP32 servo controller ready (ESP32Servo)");
}

void loop() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (inputLine.length() > 0) {
        processLine(inputLine);
        inputLine = "";
      }
    } else {
      inputLine += c;
    }
  }
}
