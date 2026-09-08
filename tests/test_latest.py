from __future__ import annotations

import asyncio
import importlib.util
import os
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
LATEST_PATH = ROOT / "app" / "latest.py"


class _Intents:
    def __init__(self):
        self.message_content = False
        self.reactions = False

    @classmethod
    def default(cls):
        return cls()


class _Client:
    def __init__(self, **_kwargs):
        self.user = None

    def event(self, function):
        setattr(self, function.__name__, function)
        return function

    async def wait_for(self, *_args, **_kwargs):
        raise asyncio.TimeoutError

    def get_channel(self, _channel_id):
        return None

    def run(self, _token):
        raise AssertionError("bot.run must not execute while importing tests")


class _File:
    def __init__(self, path):
        self.path = path


class _SentMessage:
    id = 9001

    async def add_reaction(self, _emoji):
        return None


class _Channel:
    id = 123

    def __init__(self):
        self.messages = []

    async def send(self, content=None, **_kwargs):
        self.messages.append(content)
        return _SentMessage()


class _Author:
    id = 456
    bot = False
    display_name = "Tester"


class _Message:
    id = 789
    webhook_id = None
    content = ""
    author = _Author()

    def __init__(self):
        self.channel = _Channel()


def _install_stub_modules():
    discord = types.ModuleType("discord")
    discord.Intents = _Intents
    discord.Client = _Client
    discord.File = _File
    discord.Message = _Message
    discord.Reaction = type("Reaction", (), {})
    discord.User = _Author

    dotenv = types.ModuleType("dotenv")
    dotenv.load_dotenv = lambda: None

    bcs = types.ModuleType("bennycaresystem")
    drivers = types.ModuleType("bennycaresystem.drivers")
    status = types.ModuleType("bennycaresystem.status")

    webcam = types.ModuleType("bennycaresystem.drivers.webcam_util")
    webcam.capture_snapshot = lambda: "/tmp/proof.jpg"

    kibble = types.ModuleType("bennycaresystem.drivers.kibble_driver")
    kibble.drop_kibble_bins = lambda _bins: True

    audio = types.ModuleType("bennycaresystem.drivers.kibble_audio_driver")
    audio.play_kibble_shake = lambda: True
    audio.play_emergency_wakeup = lambda: True
    audio.play_benny_lets_eat = lambda: True

    honey = types.ModuleType("bennycaresystem.drivers.honey_driver")
    honey.push_actuator_ml = lambda _ml: True
    honey.push_honey_ml = lambda _ml: True
    honey.push_honey_g = lambda _grams: True
    honey.retract_ml = lambda _ml: True
    honey.retract_g = lambda _grams: True

    status_builder = types.ModuleType("bennycaresystem.status.status_builder")
    status_builder.build_status = lambda *_locks: "ok"

    sys.modules.update(
        {
            "discord": discord,
            "dotenv": dotenv,
            "bennycaresystem": bcs,
            "bennycaresystem.drivers": drivers,
            "bennycaresystem.drivers.webcam_util": webcam,
            "bennycaresystem.drivers.kibble_driver": kibble,
            "bennycaresystem.drivers.kibble_audio_driver": audio,
            "bennycaresystem.drivers.honey_driver": honey,
            "bennycaresystem.status": status,
            "bennycaresystem.status.status_builder": status_builder,
        }
    )


def _load_latest():
    _install_stub_modules()
    os.environ["DISCORD_BOT_TOKEN"] = "test-token"
    spec = importlib.util.spec_from_file_location("tower_latest_under_test", LATEST_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


latest = _load_latest()


class LatestCommandTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        latest.camera_lock = asyncio.Lock()
        latest.honey_lock = asyncio.Lock()
        latest.kibble_lock = asyncio.Lock()
        latest.audio_lock = asyncio.Lock()
        latest.food_operation_lock = asyncio.Lock()

    async def test_feed_waits_for_honey_before_kibble_and_audio(self):
        events = []
        message = _Message()

        def honey(_grams):
            events.append("honey-complete")
            return True

        def kibble(_bins):
            events.append("kibble")
            return True

        def audio():
            events.append("letseat")
            return True

        async def observe(_message, _label):
            events.append("pictures")

        latest.push_honey_g = honey
        latest.drop_kibble_bins = kibble
        latest.play_benny_lets_eat = audio
        latest._observe_and_confirm_eating = observe

        await latest._execute_feed_sequence(message, 10.0, 1, "test rescue")

        self.assertEqual(
            events,
            ["honey-complete", "kibble", "letseat", "pictures"],
        )

    async def test_honey_failure_prevents_kibble(self):
        events = []
        message = _Message()

        def honey(_grams):
            events.append("honey-failed")
            return False

        def kibble(_bins):
            events.append("kibble")
            return True

        latest.push_honey_g = honey
        latest.drop_kibble_bins = kibble

        await latest._execute_feed_sequence(message, 10.0, 1, "test rescue")

        self.assertEqual(events, ["honey-failed"])
        self.assertIn("kibble was not attempted", message.channel.messages[-1])

    async def test_push_uses_fast_positioning_driver(self):
        calls = []
        message = _Message()
        latest.push_actuator_ml = lambda ml: calls.append(ml) or True

        await latest.handle_push(message, ["!push", "40"])

        self.assertEqual(calls, [40.0])
        self.assertIn("rapidly advanced", message.channel.messages[-1])

    async def test_retract_handler_does_not_impose_a_maximum(self):
        calls = []
        message = _Message()
        latest.retract_ml = lambda ml: calls.append(ml) or True

        await latest.handle_retract(message, ["!retract", "1000"])

        self.assertEqual(calls, [1000.0])
        self.assertIn("retracted 1000.0 mL", message.channel.messages[-1])


if __name__ == "__main__":
    unittest.main()
