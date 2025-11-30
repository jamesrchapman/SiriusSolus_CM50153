import RPi.GPIO as GPIO
import time
import sys

class PinTester:
    """
    Toggler class for a single BCM GPIO pin.
    """

    def __init__(self, pin_number):
        # Store BCM pin number
        self.pin = pin_number

        # Use BCM numbering
        GPIO.setmode(GPIO.BCM)

        # Configure pin as output
        GPIO.setup(self.pin, GPIO.OUT)

    def toggle(self, interval=1.0):
        """
        Toggle pin HIGH/LOW indefinitely.
        interval: seconds between toggles.
        """
        print(f"Toggling BCM pin {self.pin} every {interval} seconds. Ctrl+C to stop.")

        state = False
        try:
            while True:
                state = not state
                GPIO.output(self.pin, state)
                print(f"Pin {self.pin} -> {'HIGH' if state else 'LOW'}")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("Stopping toggler.")
        finally:
            GPIO.cleanup(self.pin)
            print(f"Pin {self.pin} cleaned up.")

def parse_pin_from_args():
    """
    Extract pin number from command-line arguments.
    Usage: python pin_test.py 17
    """
    if len(sys.argv) < 2:
        print("Usage: python pin_test.py <BCM_pin_number>")
        sys.exit(1)

    try:
        pin = int(sys.argv[1])
    except ValueError:
        print("Error: pin must be an integer.")
        sys.exit(1)

    return pin

if __name__ == "__main__":
    pin_to_test = parse_pin_from_args()
    tester = PinTester(pin_to_test)
    tester.toggle(interval=0.5)
