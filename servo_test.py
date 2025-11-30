import RPi.GPIO as GPIO
import time

SERVO_PIN = 17  # BCM pin number, physical pin 11

def setup_servo(pin):
    # BCM numbering
    GPIO.setmode(GPIO.BCM)

    # Set pin as output
    GPIO.setup(pin, GPIO.OUT)

    # 50 Hz PWM for servo
    pwm = GPIO.PWM(pin, 50)
    pwm.start(0)  # start with 0% duty cycle (no signal)
    return pwm

def set_angle(pwm, angle):
    """
    Move servo to an approximate angle (0-180).
    MG90S typical range ~0-180, but real range may be 0-120ish.

    Duty cycle formula is approximate:
    2.5 -> ~0°
    7.5 -> ~90°
    12.5 -> ~180°
    """
    duty = 2.5 + (angle / 180.0) * 10.0
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.5)  # give servo time to move
    pwm.ChangeDutyCycle(0)  # stop sending continuous power to avoid buzz

def main():
    pwm = setup_servo(SERVO_PIN)

    try:
        print("0 degrees")
        set_angle(pwm, 0)
        time.sleep(1)

        print("90 degrees")
        set_angle(pwm, 90)
        time.sleep(1)

        print("180 degrees")
        set_angle(pwm, 180)
        time.sleep(1)

        print("Back to 90 degrees")
        set_angle(pwm, 90)
        time.sleep(1)

    except KeyboardInterrupt:
        pass
    finally:
        pwm.stop()
        GPIO.cleanup()
        print("Clean exit.")

if __name__ == "__main__":
    main()
