import RPi.GPIO as GPIO
import time

SERVO_PIN = 17  # BCM 17 = physical pin 11

GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)

# 50 Hz PWM (standard for hobby servos)
pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(0)

def angle_to_duty(angle):
    """
    Convert angle (0-180) to duty cycle.
    Typical servo mapping:
      0deg   -> ~2.5% duty
      90deg  -> ~7.5% duty
      180deg -> ~12.5% duty
    """
    return 2.5 + (angle / 180.0) * 10.0

try:
    while True:
        # Sweep forward
        for angle in range(0, 181, 10):
            duty = angle_to_duty(angle)
            pwm.ChangeDutyCycle(duty)
            time.sleep(0.05)

        # Sweep back
        for angle in range(180, -1, -10):
            duty = angle_to_duty(angle)
            pwm.ChangeDutyCycle(duty)
            time.sleep(0.05)

except KeyboardInterrupt:
    pass
finally:
    pwm.stop()
    GPIO.cleanup()
    print("Clean exit.")
