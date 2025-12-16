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
intents = discord.Intents.none()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# ---- prevent overlapping servo runs ----
servo_lock = asyncio.Lock()

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
