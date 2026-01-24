import RPi.GPIO as GPIO
import time

SERVO_PIN = 17
PWM_FREQ = 50

def servo_rotate_once(pin=SERVO_PIN, start_duty=7.5, end_duty=12.5):
    """
    start_duty: where the servo is assumed to be
    end_duty:   target position
    """

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(pin, GPIO.OUT)

    pwm = GPIO.PWM(pin, PWM_FREQ)
    pwm.start(0)

    try:
        pwm.ChangeDutyCycle(start_duty)
        time.sleep(0.3)

        pwm.ChangeDutyCycle(end_duty)
        time.sleep(0.6)

        pwm.ChangeDutyCycle(0)

    finally:
        pwm.stop()
        GPIO.cleanup()
