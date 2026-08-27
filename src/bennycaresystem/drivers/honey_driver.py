import time

import RPi.GPIO as GPIO


print("=== Honey actuator driver loaded ===")

HONEY_FWD_PWM = 18
HONEY_REV_PWM = 19
HONEY_FWD_EN = 23
HONEY_REV_EN = 26

ML_PER_SECOND = 20 / 3.0  # 20 ml in 3 seconds, empirically measured on 2026-03-09
MAX_ML_PER_COMMAND = 20.0
MAX_DURATION_SECONDS = 15
MIN_INTERVAL_SECONDS = 0
HONEY_G_PER_ML = 1.42
MAX_G_PER_COMMAND = MAX_ML_PER_COMMAND * HONEY_G_PER_ML

# Advance the syringe gradually instead of applying one continuous forward push.
# Each powered pulse targets 1 ml using the existing actuator calibration.
FORWARD_ML_PER_PULSE = 1.0
FORWARD_PULSE_SECONDS = FORWARD_ML_PER_PULSE / ML_PER_SECOND
FORWARD_PULSE_PAUSE_SECONDS = 2.0

_last_push_time = 0


def _setup():
    GPIO.setmode(GPIO.BCM)
    for pin in (
        HONEY_FWD_PWM,
        HONEY_REV_PWM,
        HONEY_FWD_EN,
        HONEY_REV_EN,
    ):
        GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

    # Enable both halves of the bridge.
    GPIO.output(HONEY_FWD_EN, GPIO.HIGH)
    GPIO.output(HONEY_REV_EN, GPIO.HIGH)


_setup()


def _stop():
    GPIO.output(HONEY_FWD_PWM, GPIO.LOW)
    GPIO.output(HONEY_REV_PWM, GPIO.LOW)


def _run_forward(seconds: float):
    print(
        f"RUN FORWARD {seconds:.2f}s total as "
        f"{FORWARD_ML_PER_PULSE:.2f}ml pulses "
        f"({FORWARD_PULSE_SECONDS:.2f}s powered) with "
        f"{FORWARD_PULSE_PAUSE_SECONDS:.2f}s pauses"
    )

    remaining_seconds = seconds
    pulse_number = 0

    GPIO.output(HONEY_REV_PWM, GPIO.LOW)

    try:
        while remaining_seconds > 0:
            pulse_number += 1
            pulse_seconds = min(FORWARD_PULSE_SECONDS, remaining_seconds)

            print(f"FORWARD PULSE {pulse_number}: {pulse_seconds:.2f}s")
            GPIO.output(HONEY_FWD_PWM, GPIO.HIGH)
            time.sleep(pulse_seconds)
            GPIO.output(HONEY_FWD_PWM, GPIO.LOW)

            remaining_seconds = max(0.0, remaining_seconds - pulse_seconds)

            if remaining_seconds > 0:
                print(f"FORWARD PAUSE: {FORWARD_PULSE_PAUSE_SECONDS:.2f}s")
                time.sleep(FORWARD_PULSE_PAUSE_SECONDS)
    finally:
        _stop()


def _run_reverse(seconds: float):
    print(f"RUN REVERSE {seconds:.2f}s")
    GPIO.output(HONEY_FWD_PWM, GPIO.LOW)
    GPIO.output(HONEY_REV_PWM, GPIO.HIGH)
    time.sleep(seconds)
    _stop()


# ------------------------
# Seconds-based primitives
# ------------------------

def push_honey_seconds(seconds: float) -> bool:
    global _last_push_time

    now = time.time()
    if seconds <= 0 or seconds > MAX_DURATION_SECONDS:
        return False
    if now - _last_push_time < MIN_INTERVAL_SECONDS:
        return False

    try:
        _run_forward(seconds)
        _last_push_time = time.time()
        return True
    except Exception:
        _stop()
        raise


def retract_seconds(seconds: float) -> bool:
    if seconds <= 0 or seconds > MAX_DURATION_SECONDS:
        return False

    try:
        _run_reverse(seconds)
        return True
    except Exception:
        _stop()
        raise


# ------------------------
# ML interface (derived)
# ------------------------

def push_honey_ml(ml: float) -> bool:
    if ml <= 0 or ml > MAX_ML_PER_COMMAND:
        return False

    seconds = ml / ML_PER_SECOND
    return push_honey_seconds(seconds)


def retract_ml(ml: float) -> bool:
    if ml <= 0 or ml > MAX_ML_PER_COMMAND:
        return False

    seconds = ml / ML_PER_SECOND
    return retract_seconds(seconds)


# ------------------------
# G interface (derived)
# ------------------------

def push_honey_g(g: float) -> bool:
    if g <= 0 or g > MAX_G_PER_COMMAND:
        return False

    ml = g / HONEY_G_PER_ML
    return push_honey_ml(ml)


def retract_g(g: float) -> bool:
    if g <= 0 or g > MAX_G_PER_COMMAND:
        return False

    ml = g / HONEY_G_PER_ML
    return retract_ml(ml)
