// Motor pin definitions
const int IN1 = 1;
const int IN2 = 2;
const int IN3 = 3;
const int IN4 = 4;

// Steps per output shaft rotation
const int stepsPerRotation = 2048; // Approximate for 28BYJ-48

int currentStep = 0;

void setup() {
  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);
}

void moveOneStep() {
  switch (currentStep % 4) {
    case 0:
      digitalWrite(IN1, HIGH);
      digitalWrite(IN2, LOW);
      digitalWrite(IN3, LOW);
      digitalWrite(IN4, LOW);
      break;
    case 1:
      digitalWrite(IN1, LOW);
      digitalWrite(IN2, HIGH);
      digitalWrite(IN3, LOW);
      digitalWrite(IN4, LOW);
      break;
    case 2:
      digitalWrite(IN1, LOW);
      digitalWrite(IN2, LOW);
      digitalWrite(IN3, HIGH);
      digitalWrite(IN4, LOW);
      break;
    case 3:
      digitalWrite(IN1, LOW);
      digitalWrite(IN2, LOW);
      digitalWrite(IN3, LOW);
      digitalWrite(IN4, HIGH);
      break;
  }
  currentStep++;
  delay(5); // Adjust if you want slower or faster stepping
}

void loop() {
  // Rotate one output shaft turn
  for (int i = 0; i < stepsPerRotation; i++) {
    moveOneStep();  // ONE step per call
  }

  // Wait 20 seconds
  // delay(20000);
}
