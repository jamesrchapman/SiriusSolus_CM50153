import os
import asyncio
import discord
from discord import app_commands
from dotenv import load_dotenv

# ---- load env ----
load_dotenv()
BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN not set")

# ---- import hardware action ----
from servo_util import servo_rotate_once

# ---- discord setup ----
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ---- prevent overlapping servo runs ----
servo_lock = asyncio.Lock()


RESCUE_CHANNEL_ID = int(os.getenv("RESCUE_CHANNEL_ID", "0"))  # optional

# ---- MESSAGE TRIGGER (NEW) ----
@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    if RESCUE_CHANNEL_ID and message.channel.id != RESCUE_CHANNEL_ID:
        return

    content = (message.content or "").strip().lower()

    if content in ("!rescue", "rescue"):
        async with servo_lock:
            loop = asyncio.get_running_loop()
            try:
                result = await loop.run_in_executor(None, servo_rotate_once)
            except Exception as e:
                await message.channel.send(f"servo error: {type(e).__name__}: {e}")
                return

        if result is None or result is True:
            await message.channel.send("✅ rescue executed (message trigger)")
        else:
            await message.channel.send("⚠️ rescue reported failure (message trigger)")



# ---- slash command ----
@tree.command(name="rescue", description="Run the rescue servo once.")
async def rescue_cmd(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)

    async with servo_lock:
        loop = asyncio.get_running_loop()
        try:
            # run blocking GPIO code off the event loop
            result = await loop.run_in_executor(None, servo_rotate_once)
        except Exception as e:
            await interaction.followup.send(
                f"servo error: {type(e).__name__}: {e}"
            )
            return

    # treat None as success
    if result is None or result is True:
        await interaction.followup.send("✅ rescue executed")
    else:
        await interaction.followup.send("⚠️ rescue reported failure")

# ---- lifecycle ----
@bot.event
async def setup_hook():
    await tree.sync()
    print("slash commands synced")

@bot.event
async def on_ready():
    print(f"logged in as {bot.user}")

# ---- entry ----
bot.run(BOT_TOKEN)
