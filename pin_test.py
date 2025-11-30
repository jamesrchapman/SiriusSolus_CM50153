import RPi.GPIO as GPIO
import time

class PinTester:
    """
    Simple GPIO pin tester.
    Toggles a single BCM pin HIGH/LOW repeatedly.
    """

    def __init__(self, pin_number):
        # Store the BCM pin number internally
        self.pin = pin_number

        # Always use BCM numbering
        GPIO.setmode(GPIO.BCM)

        # SETUP: configure pin as output
        # try/except protects against pins already in use or garbage states
        try:
            GPIO.setup(self.pin, GPIO.OUT)
        except RuntimeError as e:
            print(f"Error setting up pin {self.pin}: {e}")
            raise

    def toggle(self, interval=1.0):
        """
        Toggle the pin HIGH/LOW at a fixed interval.
        interval: seconds between toggles.
        """
        print(f"Toggling BCM pin {self.pin} every {interval} seconds. Ctrl+C to stop.")

        try:
            state = False  # LOW to start
            while True:
                state = not state
                GPIO.output(self.pin, state)
                print(f"Pin {self.pin} set to {'HIGH' if state else 'LOW'}")
                time.sleep(interval)
        except KeyboardInterrupt:
            print("Stopping toggler.")
        finally:
            GPIO.cleanup(self.pin)
            print(f"Pin {self.pin} cleaned up.")

if __name__ == "__main__":
    # CHANGE THIS NUMBER to test different pins: e.g. 2, 3, 4, 17, 18, etc.
    tester = PinTester(pin_number=2)
    tester.toggle(interval=0.5)
