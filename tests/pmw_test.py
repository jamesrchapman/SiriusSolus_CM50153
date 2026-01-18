import RPi.GPIO as GPIO
import time

PIN = 17  # BCM 17 = physical pin 11

GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN, GPIO.OUT)

pwm = GPIO.PWM(PIN, 50)
pwm.start(0)  # start at 0% duty

try:
    while True:
        print("0% duty")
        pwm.ChangeDutyCycle(0)
        time.sleep(3)

        print("7.5% duty")
        pwm.ChangeDutyCycle(7.5)
        time.sleep(3)

        print("12.5% duty")
        pwm.ChangeDutyCycle(12.5)
        time.sleep(3)

finally:
    pwm.stop()
    GPIO.cleanup()
