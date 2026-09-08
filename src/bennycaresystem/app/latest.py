from __future__ import annotations

import asyncio
import math
import os

import discord
from dotenv import load_dotenv


# ---- load env ----
load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN not set")


# ---- import hardware actions ----
from bennycaresystem.drivers.webcam_util import capture_snapshot
from bennycaresystem.drivers.kibble_driver import drop_kibble_bins
from bennycaresystem.drivers.kibble_audio_driver import (
    play_kibble_shake,
    play_emergency_wakeup,
    play_benny_lets_eat,
)
from bennycaresystem.drivers.honey_driver import (
    push_actuator_ml,
    push_honey_ml,
    push_honey_g,
    retract_ml,
    retract_g,
)
from bennycaresystem.status.status_builder import build_status


# ---- discord setup ----
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
bot = discord.Client(intents=intents)


# ---- prevent overlapping runs ----
camera_lock = asyncio.Lock()
honey_lock = asyncio.Lock()
kibble_lock = asyncio.Lock()
audio_lock = asyncio.Lock()

# Every operation that moves either food mechanism takes this lock. This keeps
# manual commands from interleaving with an automatic honey -> kibble sequence.
food_operation_lock = asyncio.Lock()

RESCUE_CHANNEL_ID = int(os.getenv("RESCUE_CHANNEL_ID", "0"))  # optional
EATING_CONFIRMATION_TIMEOUT_SECONDS = int(
    os.getenv("EATING_CONFIRMATION_TIMEOUT_SECONDS", "600")
)


def _snapshot_delays_seconds() -> tuple[float, ...]:
    raw = os.getenv("FEED_SNAPSHOT_DELAYS_SECONDS", "0,10,30")

    try:
        delays = tuple(sorted({float(value.strip()) for value in raw.split(",")}))
    except ValueError:
        return (0.0, 10.0, 30.0)

    valid = tuple(delay for delay in delays if math.isfinite(delay) and delay >= 0)
    return valid or (0.0, 10.0, 30.0)


FEED_SNAPSHOT_DELAYS_SECONDS = _snapshot_delays_seconds()


# ---- blocking hardware helpers ----

async def _run_hardware(lock: asyncio.Lock, function, *args):
    async with lock:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, function, *args)


async def _capture_and_send(message: discord.Message, caption: str) -> bool:
    path = None

    try:
        path = await _run_hardware(camera_lock, capture_snapshot)
        await message.channel.send(
            content=caption,
            file=discord.File(path),
        )
        return True
    except Exception as error:
        await message.channel.send(
            f"⚠️ snapshot failed: {type(error).__name__}: {error}"
        )
        return False
    finally:
        if path:
            try:
                os.remove(path)
            except OSError:
                pass


async def _observe_and_confirm_eating(
    message: discord.Message,
    sequence_label: str,
):
    previous_delay = 0.0
    captured = 0

    for number, delay_seconds in enumerate(FEED_SNAPSHOT_DELAYS_SECONDS, start=1):
        await asyncio.sleep(max(0.0, delay_seconds - previous_delay))
        previous_delay = delay_seconds

        if await _capture_and_send(
            message,
            (
                f"📷 {sequence_label} follow-up {number}/"
                f"{len(FEED_SNAPSHOT_DELAYS_SECONDS)} "
                f"(+{delay_seconds:g}s)"
            ),
        ):
            captured += 1

    prompt = await message.channel.send(
        f"Benny eating check — {captured} picture(s) captured. "
        "React ✅ if he came and ate, or ❌ if he did not."
    )
    await prompt.add_reaction("✅")
    await prompt.add_reaction("❌")

    def reaction_check(reaction: discord.Reaction, user: discord.User) -> bool:
        return (
            reaction.message.id == prompt.id
            and not user.bot
            and str(reaction.emoji) in {"✅", "❌"}
        )

    try:
        reaction, user = await bot.wait_for(
            "reaction_add",
            timeout=EATING_CONFIRMATION_TIMEOUT_SECONDS,
            check=reaction_check,
        )
    except asyncio.TimeoutError:
        await message.channel.send(
            f"⚠️ {sequence_label}: eating was not confirmed within "
            f"{EATING_CONFIRMATION_TIMEOUT_SECONDS // 60} minutes."
        )
        return

    if str(reaction.emoji) == "✅":
        await message.channel.send(
            f"✅ {sequence_label}: {user.display_name} confirmed Benny came and ate."
        )
    else:
        await message.channel.send(
            f"🚨 {sequence_label}: {user.display_name} reported that Benny did not eat."
        )


# ---- handler functions ----

async def handle_snapshot(message: discord.Message):
    await _capture_and_send(message, "📷 snapshot captured")


async def handle_audio(
    message: discord.Message,
    playback_fn,
    success_message: str,
):
    result = await _run_hardware(audio_lock, playback_fn)

    if result:
        await message.channel.send(success_message)
    else:
        await message.channel.send("⚠️ audio failed")


async def handle_status(message: discord.Message):
    status_text = build_status(
        honey_lock,
        kibble_lock,
        camera_lock,
    )
    await message.channel.send(f"```\n{status_text}\n```")


async def handle_honey(message: discord.Message, parts):
    if len(parts) != 2:
        await message.channel.send("usage: !honey <ml>")
        return

    try:
        ml = float(parts[1])
    except ValueError:
        await message.channel.send("invalid ml value")
        return

    async with food_operation_lock:
        result = await _run_hardware(honey_lock, push_honey_ml, ml)

    if result:
        await message.channel.send(f"🍯 pushed {ml} mL")
    else:
        await message.channel.send("⚠️ honey push rejected or failed")


async def handle_push(message: discord.Message, parts):
    if len(parts) != 2:
        await message.channel.send("usage: !push <ml>")
        return

    try:
        ml = float(parts[1])
    except ValueError:
        await message.channel.send("invalid ml value")
        return

    async with food_operation_lock:
        result = await _run_hardware(honey_lock, push_actuator_ml, ml)

    if result:
        await message.channel.send(f"⏩ rapidly advanced actuator {ml} mL")
    else:
        await message.channel.send("⚠️ actuator push rejected or failed")


async def handle_kibble(message: discord.Message, parts):
    if len(parts) != 2:
        await message.channel.send("usage: !kibble <bins>")
        return

    try:
        bins = int(parts[1])
    except ValueError:
        await message.channel.send("invalid bin count")
        return

    async with food_operation_lock:
        result = await _run_hardware(kibble_lock, drop_kibble_bins, bins)

    if result:
        await message.channel.send(f"🥣 dropped {bins} bins")
    else:
        await message.channel.send("⚠️ kibble drop failed")


async def handle_retract(message: discord.Message, parts):
    if len(parts) != 2:
        await message.channel.send("usage: !retract <ml>")
        return

    try:
        ml = float(parts[1])
    except ValueError:
        await message.channel.send("invalid ml value")
        return

    async with food_operation_lock:
        result = await _run_hardware(honey_lock, retract_ml, ml)

    if result:
        await message.channel.send(f"↩️ retracted {ml} mL")
    else:
        await message.channel.send("⚠️ retract rejected")


async def handle_retractg(message: discord.Message, parts):
    if len(parts) != 2:
        await message.channel.send("usage: !retractg <grams>")
        return

    try:
        grams = float(parts[1])
    except ValueError:
        await message.channel.send("invalid gram value")
        return

    async with food_operation_lock:
        result = await _run_hardware(honey_lock, retract_g, grams)

    if result:
        await message.channel.send(f"↩️ retracted {grams} g honey")
    else:
        await message.channel.send("⚠️ retract rejected")


async def handle_honeyg(message: discord.Message, parts):
    if len(parts) != 2:
        await message.channel.send("usage: !honeyg <grams>")
        return

    try:
        grams = float(parts[1])
    except ValueError:
        await message.channel.send("invalid gram value")
        return

    async with food_operation_lock:
        result = await _run_hardware(honey_lock, push_honey_g, grams)

    if result:
        await message.channel.send(f"🍯 pushed {grams} g honey")
    else:
        await message.channel.send("⚠️ honey push rejected or failed")


async def _execute_feed_sequence(
    message: discord.Message,
    honey_grams: float,
    kibble_bins: int,
    sequence_label: str,
):
    if (
        not math.isfinite(honey_grams)
        or honey_grams < 0
        or kibble_bins < 0
        or (honey_grams == 0 and kibble_bins == 0)
    ):
        await message.channel.send("⚠️ feed values must be finite and non-negative")
        return

    completed_parts = []

    # This is the physical ordering boundary. The blocking honey function must
    # return before the kibble driver is even called.
    async with food_operation_lock:
        if honey_grams > 0:
            honey_result = await _run_hardware(
                honey_lock,
                push_honey_g,
                honey_grams,
            )

            if not honey_result:
                await message.channel.send(
                    f"🚨 {sequence_label} stopped: honey failed; kibble was not attempted."
                )
                return

            completed_parts.append(f"{honey_grams:g} g honey completed")

        if kibble_bins > 0:
            kibble_result = await _run_hardware(
                kibble_lock,
                drop_kibble_bins,
                kibble_bins,
            )

            if not kibble_result:
                partial = "; ".join(completed_parts) or "no food completed"
                await message.channel.send(
                    f"🚨 {sequence_label} partially failed: {partial}; kibble failed."
                )
                return

            completed_parts.append(f"{kibble_bins} kibble bin(s) dropped")

        audio_result = await _run_hardware(audio_lock, play_benny_lets_eat)

    summary = " → ".join(completed_parts)
    if audio_result:
        summary += " → let's-eat call played"
    else:
        summary += " → ⚠️ let's-eat audio failed"

    await message.channel.send(f"✅ {sequence_label} complete: {summary}")
    await _observe_and_confirm_eating(message, sequence_label)


async def handle_feed(message: discord.Message, parts):
    if len(parts) != 3:
        await message.channel.send("usage: !feed <honey_grams> <kibble_bins>")
        return

    try:
        honey_grams = float(parts[1])
        kibble_bins = int(parts[2])
    except ValueError:
        await message.channel.send("invalid feed value")
        return

    await _execute_feed_sequence(
        message=message,
        honey_grams=honey_grams,
        kibble_bins=kibble_bins,
        sequence_label="feed sequence",
    )


async def handle_rescue(message: discord.Message, parts):
    if len(parts) != 2:
        await message.channel.send("usage: !rescue <honey_grams>")
        return

    try:
        honey_grams = float(parts[1])
    except ValueError:
        await message.channel.send("invalid honey gram value")
        return

    await _execute_feed_sequence(
        message=message,
        honey_grams=honey_grams,
        kibble_bins=1,
        sequence_label="glucose rescue",
    )


# ---- MESSAGE TRIGGER ----
@bot.event
async def on_message(message: discord.Message):
    print(
        "MESSAGE EVENT",
        message.id,
        repr(message.content),
        "author=", message.author,
        "author_id=", getattr(message.author, "id", None),
        "author_bot=", getattr(message.author, "bot", None),
        "webhook_id=", message.webhook_id,
        "channel_id=", message.channel.id,
    )

    # Ignore the BCS bot itself only.
    if bot.user and message.author.id == bot.user.id:
        return

    if RESCUE_CHANNEL_ID and message.channel.id != RESCUE_CHANNEL_ID:
        return

    # Allow either normal human messages or webhook messages. Reject other
    # bot-authored traffic that is not a webhook.
    if message.author.bot and message.webhook_id is None:
        return

    content = (message.content or "").strip().lower()
    parts = content.split()

    if not parts:
        return

    command = parts[0]

    if command == "!snapshot":
        await handle_snapshot(message)

    elif command in ("!kibblesound", "!shake"):
        await handle_audio(
            message,
            play_kibble_shake,
            "🔊 kibble shake",
        )

    elif command in ("!letseat", "!eatcall"):
        await handle_audio(
            message,
            play_benny_lets_eat,
            "🔊 Benny, let's eat",
        )

    elif command in ("!emergencywakeup", "!wakeup"):
        await handle_audio(
            message,
            play_emergency_wakeup,
            "🚨 emergency wakeup audio",
        )

    elif command == "!honey":
        await handle_honey(message, parts)

    elif command == "!push":
        await handle_push(message, parts)

    elif command == "!kibble":
        await handle_kibble(message, parts)

    elif command == "!retract":
        await handle_retract(message, parts)

    elif command == "!retractg":
        await handle_retractg(message, parts)

    elif command == "!honeyg":
        await handle_honeyg(message, parts)

    elif command == "!feed":
        await handle_feed(message, parts)

    elif command == "!rescue":
        await handle_rescue(message, parts)

    elif command == "!status":
        await handle_status(message)


# ---- lifecycle ----
@bot.event
async def on_ready():
    print(f"logged in as {bot.user}")

    if RESCUE_CHANNEL_ID:
        channel = bot.get_channel(RESCUE_CHANNEL_ID)
        if channel:
            asyncio.create_task(shadow_protocol_loop(channel))


# ---- shadow mode hook for autoprotocols ----
async def shadow_protocol_loop(channel):
    """
    Watches glucose stream and reports what the protocol
    *would* do without executing actuators.
    """
    while True:
        await asyncio.sleep(60)

        # placeholder
        decision = None

        if decision:
            await channel.send(
                f"[BCS SHADOW]\n"
                f"protocol would intervene: {decision}"
            )


# ---- entry ----
if __name__ == "__main__":
    bot.run(BOT_TOKEN)
