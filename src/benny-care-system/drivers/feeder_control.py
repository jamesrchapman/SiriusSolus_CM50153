# feeder_control.py
# BCM17 -> MOSFET gate (motor enable)
# BCM18 -> Microswitch NO contact (COM -> GND)
# Counts "press-release" cycles as portions.

from gpiozero import LED, Button
from time import monotonic, sleep

GATE_PIN = 17         # MOSFET gate
FEEDBACK_PIN = 18     # microswitch NO -> BCM18, COM -> GND

# Tune these to your hardware
DEBOUNCE_S = 0.01     # 10 ms software debounce
MIN_CYCLE_S = 0.08    # ignore cycles faster than this (bounce/noise)
MAX_RUN_S = 10.0      # failsafe: stop motor if no portions completed by then

motor = LED(GATE_PIN)
# pull_up=True -> uses Pi's internal pull-up; active LOW on press
switch = Button(FEEDBACK_PIN, pull_up=True, bounce_time=DEBOUNCE_S)

def dispense(portions: int) -> bool:
    """
    Run motor until `portions` full press-release cycles are observed.
    Returns True on success, False on timeout.
    """
    done = 0
    last_cycle_t = 0.0
    pressed = False
    start = monotonic()

    motor.on()
    try:
        while done < portions:
            now = monotonic()

            # Failsafe timeout
            if now - start > MAX_RUN_S:
                print(f"[fail] timeout after {MAX_RUN_S}s; portions={done}/{portions}")
                return False

            # Read current state (active low)
            is_pressed = switch.is_pressed  # True when lever is actuated

            # Rising phase: detect new press (LOW), remember it
            if is_pressed and not pressed:
                pressed = True

            # Falling phase: detect release (HIGH) -> counts 1 cycle
            elif (not is_pressed) and pressed:
                pressed = False
                # Debounced full cycle detected
                if (now - last_cycle_t) >= MIN_CYCLE_S:
                    done += 1
                    last_cycle_t = now
                    print(f"[tick] {done}/{portions}")
                # else: ignore as bounce

            sleep(0.002)  # 2 ms poll; low CPU, quick response

        return True
    finally:
        motor.off()

if __name__ == "__main__":
    ok = dispense(portions=3)
    print("done" if ok else "stopped")
