from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
DRIVER_PATH = ROOT / "library_sources" / "honey_driver.py"


class _GPIO(types.ModuleType):
    BCM = "BCM"
    OUT = "OUT"
    LOW = 0
    HIGH = 1

    def __init__(self):
        super().__init__("RPi.GPIO")
        self.outputs = []

    def setmode(self, _mode):
        return None

    def setup(self, *_args, **_kwargs):
        return None

    def output(self, pin, value):
        self.outputs.append((pin, value))


def _load_driver():
    gpio = _GPIO()
    rpi = types.ModuleType("RPi")
    rpi.GPIO = gpio
    sys.modules["RPi"] = rpi
    sys.modules["RPi.GPIO"] = gpio

    spec = importlib.util.spec_from_file_location("honey_driver_under_test", DRIVER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module, gpio


class HoneyDriverTests(unittest.TestCase):
    def setUp(self):
        self.driver, self.gpio = _load_driver()

    def test_fast_push_is_one_continuous_forward_run(self):
        sleeps = []

        with patch.object(self.driver.time, "sleep", side_effect=sleeps.append):
            self.assertTrue(self.driver.push_actuator_ml(40.0))

        self.assertEqual(sleeps, [6.0])
        self.assertIn(
            (self.driver.HONEY_FWD_PWM, self.driver.GPIO.HIGH),
            self.gpio.outputs,
        )
        self.assertEqual(
            self.gpio.outputs[-2:],
            [
                (self.driver.HONEY_FWD_PWM, self.driver.GPIO.LOW),
                (self.driver.HONEY_REV_PWM, self.driver.GPIO.LOW),
            ],
        )

    def test_retract_has_no_software_maximum(self):
        sleeps = []

        with patch.object(self.driver.time, "sleep", side_effect=sleeps.append):
            self.assertTrue(self.driver.retract_ml(1000.0))

        self.assertEqual(sleeps, [150.0])

    def test_normal_honey_command_keeps_its_dose_limit(self):
        self.assertFalse(self.driver.push_honey_ml(20.1))


if __name__ == "__main__":
    unittest.main()
