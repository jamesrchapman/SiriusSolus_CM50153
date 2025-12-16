# feeder_bot.py
# Adds:
#   /graph [hours]           -> plot from glucose_log.csv (+ event overlays)
#   /log_food <amount> [u]   -> write food event
#   /exercise_start [note]   -> start an exercise session + reminders
#   /exercise_finish [note]  -> end the active session
#   /exercise_brief [note]   -> single exercise blip
#
# Reminders:
#   every 20 minutes after start, if not finished, ping the originating channel:
#   "still going?" (suppresses repeat until another 20m passes)

from __future__ import annotations
import os, io, csv, asyncio, time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional, Deque, List, Dict
from collections import deque

import requests
import monkey_patch_librelinkup_tz  # must be first
from dotenv import load_dotenv
from zoneinfo import ZoneInfo
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import discord
from discord import app_commands
from libre_link_up import LibreLinkUpClient
from feeder_control import dispense  # your motor function
from servo_util import servo_rotate_once  # <-- add this


rescue_lock = asyncio.Lock()


# ============================ CONFIG =========================================

load_dotenv()

BOT_TOKEN         = os.getenv("DISCORD_BOT_TOKEN", "")
LIBRE_USER        = os.getenv("LIBRE_LINK_UP_USERNAME", "")
LIBRE_PWD         = os.getenv("LIBRE_LINK_UP_PASSWORD", "")
LIBRE_URL         = os.getenv("LIBRE_LINK_UP_URL", "https://api.libreview.io")
LIBRE_VER         = os.getenv("LIBRE_LINK_UP_VERSION", "4.16.0")
LOCAL_TZ_NAME     = os.getenv("LOCAL_TZ", "America/Los_Angeles")

POLL_SEC          = int(os.getenv("POLL_SEC", "60"))
WINDOW_MIN        = int(os.getenv("WINDOW_MIN", "20"))
LOW_HORIZ_MIN     = int(os.getenv("LOW_HORIZ_MIN", "60"))
HIGH_HORIZ_MIN    = int(os.getenv("HIGH_HORIZ_MIN", "30"))

GLUCOSE_CSV       = os.getenv("GLUCOSE_CSV", "glucose_log.csv")   # from your watcher
EVENTS_CSV        = os.getenv("EVENTS_CSV",  "events_log.csv")    # sidecar for food/exercise
REMIND_MIN        = int(os.getenv("REMIND_MIN", "20"))            # reminder spacing

FEEDER_POST_URL   = os.getenv("FEEDER_POST_URL")
FEEDER_AUTH       = os.getenv("FEEDER_AUTH_TOKEN")

# ============================ TYPES ==========================================

@dataclass
class Reading:
    ts_utc: datetime
    mgdl: float

@dataclass
class ExerciseState:
    # tracks an active session for reminders
    started_utc: datetime
    channel_id: int
    guild_id: Optional[int]
    last_ping_utc: Optional[datetime] = None
    note: Optional[str] = None

# ============================ UTILS ==========================================

TZ = ZoneInfo(LOCAL_TZ_NAME)

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def parse_iso_utc(s: str) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None

def ensure_events_header():
    if not os.path.exists(EVENTS_CSV):
        with open(EVENTS_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            # columns: timestamp, kind, detail, amount, unit, note, status
            w.writerow(["ts_utc_iso","kind","detail","amount","unit","note","status"])

def append_event(kind: str, detail: str, amount: Optional[float]=None, unit: Optional[str]=None,
                 note: Optional[str]=None, status: Optional[str]=None) -> None:
    ensure_events_header()
    with open(EVENTS_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            now_utc().isoformat(),
            kind,
            detail,
            "" if amount is None else amount,
            "" if unit   is None else unit,
            "" if note   is None else note,
            "" if status is None else status
        ])

def request_feed(portions: int) -> tuple[bool, str]:
    if not FEEDER_POST_URL:
        return False, "FEEDER_POST_URL not set"
    try:
        payload = {"portions": int(portions), "unit_g": 6}
        headers = {"Content-Type": "application/json"}
        if FEEDER_AUTH:
            headers["Authorization"] = f"Bearer {FEEDER_AUTH}"
        r = requests.post(FEEDER_POST_URL, headers=headers, json=payload, timeout=5)
        if r.status_code >= 300:
            return False, f"HTTP {r.status_code}: {r.text[:200]}"
        return True, "queued"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

# ----- glucose CSV persistence (same schema as your watcher) -----

def ensure_glucose_header():
    # create file with header if missing
    if not os.path.exists(GLUCOSE_CSV):
        with open(GLUCOSE_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["ts_utc_iso", "mgdl", "source"])

def append_glucose_row(r: Reading, source: str = "linkup") -> None:
    # append one row; explicit flush to keep file up to date
    with open(GLUCOSE_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([r.ts_utc.isoformat(), f"{r.mgdl:.2f}", source])



# ============================ LLU WATCHER ====================================

class RollingWindow:
    def __init__(self, window_minutes: int):
        self.window_sec = window_minutes * 60
        self.buf: Deque[Reading] = deque()

    def add(self, r: Reading):
        self.buf.append(r)
        cutoff = r.ts_utc.timestamp() - self.window_sec
        while self.buf and self.buf[0].ts_utc.timestamp() < cutoff:
            self.buf.popleft()

    def avg(self) -> Optional[float]:
        if not self.buf: return None
        return sum(r.mgdl for r in self.buf) / len(self.buf)

    def slope(self) -> float:
        if len(self.buf) < 2: return 0.0
        latest = self.buf[-1].ts_utc
        # OLS on minutes relative to latest
        sx = sy = sxx = sxy = 0.0; n = 0
        for r in self.buf:
            x = (r.ts_utc - latest).total_seconds()/60.0
            y = r.mgdl
            sx += x; sy += y; sxx += x*x; sxy += x*y; n += 1
        denom = n*sxx - sx*sx
        return 0.0 if abs(denom) < 1e-12 else (n*sxy - sx*sy)/denom

class LibreWatcher:
    def __init__(self):
        self.client = LibreLinkUpClient(username=LIBRE_USER, password=LIBRE_PWD, url=LIBRE_URL, version=LIBRE_VER)
        self.client.login()
        self.window = RollingWindow(WINDOW_MIN)
        self._seen_unix: Optional[float] = None
        self.latest: Optional[Reading] = None

    def fetch_once(self) -> Optional[Reading]:
        m = self.client.get_latest_reading()
        d = m.model_dump(mode="json")
        val = d.get("value_in_mg_per_dl") or d.get("glucose_value_mgdl") or d.get("value_mgdl") or d.get("value")
        ts  = d.get("unix_timestamp")     or d.get("timestamp_iso")      or d.get("timestamp")      or d.get("time")
        if val is None or ts is None:
            return None
        if isinstance(ts, (int, float)):
            sec = ts / 1000.0 if ts > 1e12 else ts
            dt = datetime.fromtimestamp(sec, tz=timezone.utc)
        else:
            # iso-ish
            dt = parse_iso_utc(str(ts)) or now_utc()
        return Reading(dt, float(val))

    def tick(self) -> dict:
        r = self.fetch_once()
        if r:
            u = r.ts_utc.timestamp()
            if self._seen_unix != u:
                self._seen_unix = u
                self.window.add(r)
                self.latest = r
                try:
                    append_glucose_row(r,source="linkup")
                except Exception as e:
                    print(f"[persist] {type(e).__name__}: {e}")
        avg = self.window.avg()
        slope = self.window.slope()
        proj_low  = None if avg is None else avg + slope * LOW_HORIZ_MIN
        proj_high = None if avg is None else avg + slope * HIGH_HORIZ_MIN
        return {"latest": self.latest, "avg": avg, "slope": slope, "proj_low": proj_low, "proj_high": proj_high}

# ============================ GRAPH FROM CSV =================================

def read_glucose_csv_last_hours(hours: int) -> List[Reading]:
    """Read last N hours from glucose_log.csv (columns: ts_utc_iso, mgdl, source)."""
    out: List[Reading] = []
    if not os.path.exists(GLUCOSE_CSV):
        return out
    cutoff = now_utc().timestamp() - hours*3600
    with open(GLUCOSE_CSV, "r", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        # tolerate either 3-column header or additional cols
        for row in rd:
            ts = parse_iso_utc(row.get("ts_utc_iso",""))
            try:
                mg = float(row.get("mgdl",""))
            except Exception:
                continue
            if not ts: continue
            if ts.timestamp() >= cutoff:
                out.append(Reading(ts, mg))
    return out

def read_events_last_hours(hours: int) -> List[dict]:
    """Read events within last N hours for overlays."""
    events = []
    if not os.path.exists(EVENTS_CSV):
        return events
    cutoff = now_utc().timestamp() - hours*3600
    with open(EVENTS_CSV, "r", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for row in rd:
            ts = parse_iso_utc(row.get("ts_utc_iso",""))
            if not ts: continue
            if ts.timestamp() >= cutoff:
                events.append(row | {"ts": ts})
    return events

def make_graph_png(hours: int) -> io.BytesIO:
    series = read_glucose_csv_last_hours(hours)
    buf = io.BytesIO()
    if len(series) < 2:
        # small placeholder
        plt.figure(figsize=(6,2.5), dpi=160)
        plt.title(f"Not enough data in last {hours}h")
        plt.tight_layout(); plt.savefig(buf, format="png"); plt.close(); buf.seek(0); return buf

    xs = [r.ts_utc.astimezone(TZ) for r in series]
    ys = [r.mgdl for r in series]

    # simple SMA over ~WINDOW_MIN minutes using an approximate sample count
    # derive sample interval from timestamps (median)
    if len(xs) >= 3:
        dts = [(xs[i]-xs[i-1]).total_seconds() for i in range(1,len(xs))]
        dts.sort()
        median_sec = dts[len(dts)//2]
        samples_k = max(1, int((WINDOW_MIN*60)/max(1, median_sec)))
    else:
        samples_k = 1

    def sma(vals, k):
        if k <= 1: return vals[:]
        out=[]; q=deque(); s=0.0
        for v in vals:
            q.append(v); s+=v
            if len(q) > k: s-=q.popleft()
            out.append(s/len(q))
        return out

    events = read_events_last_hours(hours)

    plt.figure(figsize=(9,4), dpi=160)
    plt.plot(xs, ys, linewidth=1.5, label="mg/dL")
    if samples_k>1 and len(ys)>=samples_k:
        plt.plot(xs, sma(ys, samples_k), linewidth=1.2, linestyle="--", label=f"SMA~{WINDOW_MIN}m")

    # overlays: food = vertical line + label; exercise start/finish/brief markers
    for e in events:
        kind = (e.get("kind") or "").lower()
        tloc = e["ts"].astimezone(TZ)
        if kind == "food":
            amt = e.get("amount") or ""
            unit = e.get("unit") or ""
            lbl = f"food {amt}{unit}".strip()
            plt.axvline(tloc, linewidth=1.0, alpha=0.35)
            plt.text(tloc, max(ys)+5, lbl, rotation=90, va="bottom", ha="center", fontsize=8)
        elif kind in ("exercise_start","exercise_finish","exercise_brief"):
            tag = {"exercise_start":"ex start","exercise_finish":"ex end","exercise_brief":"ex"}[kind]
            plt.scatter([tloc],[ys[-1]], s=16)  # y at latest just for visibility
            plt.text(tloc, ys[-1], tag, rotation=90, va="bottom", ha="center", fontsize=7)

    plt.title(f"Glucose — last {hours}h (local {LOCAL_TZ_NAME})")
    plt.xlabel("time"); plt.ylabel("mg/dL")
    plt.grid(True, alpha=0.3); plt.legend(loc="upper left")
    plt.tight_layout(); plt.savefig(buf, format="png"); plt.close(); buf.seek(0)
    return buf


def warm_window_from_csv(watcher: "LibreWatcher", minutes: int):
    cutoff = now_utc().timestamp() - minutes*60
    if not os.path.exists(GLUCOSE_CSV):
        return
    try:
        with open(GLUCOSE_CSV, "r", encoding="utf-8") as f:
            rd = csv.DictReader(f)
            rows = [row for row in rd if row.get("ts_utc_iso") and row.get("mgdl")]
        # keep only recent rows
        recent = []
        for row in rows:
            ts = parse_iso_utc(row["ts_utc_iso"])
            if not ts:
                continue
            if ts.timestamp() >= cutoff:
                try:
                    mg = float(row["mgdl"])
                except Exception:
                    continue
                recent.append(Reading(ts, mg))
        # push into window in order
        recent.sort(key=lambda x: x.ts_utc)
        for r in recent:
            watcher.window.add(r)
        if recent:
            watcher.latest = recent[-1]
            watcher._seen_unix = recent[-1].ts_utc.timestamp()
            print(f"[warm] window primed with {len(recent)} points")
    except Exception as e:
        print(f"[warm] {type(e).__name__}: {e}")


# ============================ DISCORD BOT ====================================

intents = discord.Intents.none()
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)


SYNCED_ONCE = False


watcher: Optional[LibreWatcher] = None
latest_snapshot: Optional[dict] = None

# in-memory single active exercise session (simple; per-server/channel if you want)
active_exercise: Optional[ExerciseState] = None

async def poller():
    global latest_snapshot
    last_seen = None
    while True:
        try:
            if watcher:
                snap = watcher.tick()
                if snap:
                    latest_snapshot = snap
                    r = snap.get("latest")
                    if r:
                        ts = r.ts_utc.timestamp()
                        if ts != last_seen:
                            last_seen = ts
                            print(f"[poll] {r.ts_utc.astimezone(TZ).isoformat()}  {r.mgdl:.0f} mg/dL")
        except Exception as e:
            print(f"[poll] {type(e).__name__}: {e}")
        await asyncio.sleep(POLL_SEC)


async def exercise_reminder_loop():
    # checks every minute; pings each REMIND_MIN window
    global active_exercise
    while True:
        try:
            if active_exercise:
                now = now_utc()
                last = active_exercise.last_ping_utc or active_exercise.started_utc
                if (now - last) >= timedelta(minutes=REMIND_MIN):
                    ch = bot.get_channel(active_exercise.channel_id)
                    if ch:
                        await ch.send("exercise started earlier — still going?")
                        active_exercise.last_ping_utc = now
        except Exception as e:
            print(f"[remind] {type(e).__name__}: {e}")
        await asyncio.sleep(60)

# ---------- slash commands ----------

@tree.command(name="last", description="Show last glucose reading and projections (from live poller).")
async def last_cmd(interaction: discord.Interaction):
    await interaction.response.defer(thinking=False)
    s = latest_snapshot or {}
    r: Reading = s.get("latest")
    if not r:
        await interaction.followup.send("no data yet")
        return
    loc = r.ts_utc.astimezone(TZ).isoformat()
    avg = s.get("avg"); slope = s.get("slope")
    proj_low = s.get("proj_low"); proj_high = s.get("proj_high")

    def fmt(x): return "—" if x is None else f"{x:.1f}"

    embed = discord.Embed(title="Last Reading", description=f"{r.mgdl:.0f} mg/dL", timestamp=now_utc())
    embed.add_field(name="Local time", value=loc, inline=False)
    embed.add_field(name="Avg", value=fmt(avg), inline=True)
    embed.add_field(name="Slope (mg/dL/min)", value=f"{slope:.3f}", inline=True)
    embed.add_field(name=f"Proj {LOW_HORIZ_MIN}m", value=fmt(proj_low), inline=True)
    embed.add_field(name=f"Proj {HIGH_HORIZ_MIN}m", value=fmt(proj_high), inline=True)
    await interaction.followup.send(embed=embed)

@tree.command(name="graph", description="Plot last N hours from CSV log (default 8).")
@app_commands.describe(hours="Hours to plot (1–48)")
async def graph_cmd(interaction: discord.Interaction, hours: Optional[int] = 8):
    hours = 8 if hours is None else max(1, min(48, int(hours)))
    await interaction.response.defer(thinking=True)
    buf = make_graph_png(hours)
    await interaction.followup.send(file=discord.File(buf, filename=f"glucose_{hours}h.png"))

@tree.command(name="log_food", description="Log food: amount + unit (e.g., 15 g, or 2 portions).")
@app_commands.describe(amount="numeric amount", unit="e.g. g, portions")
async def log_food_cmd(interaction: discord.Interaction, amount: float, unit: Optional[str] = "g"):
    append_event("food", "dry", amount=amount, unit=unit or "")
    await interaction.response.send_message(f"logged food: {amount} {unit or ''}")

@tree.command(name="exercise_start", description="Mark start of exercise (optional note).")
@app_commands.describe(note="e.g., walk, sprints, play")
async def exercise_start_cmd(interaction: discord.Interaction, note: Optional[str] = None):
    global active_exercise
    append_event("exercise_start", "start", note=note or "")
    active_exercise = ExerciseState(
        started_utc=now_utc(),
        channel_id=interaction.channel_id,
        guild_id=interaction.guild_id,
        note=note or None
    )
    await interaction.response.send_message("exercise started")


@tree.command(name="rescue", description="Run the rescue servo action once.")
async def rescue_cmd(interaction: discord.Interaction):
    # Immediate ack so Discord doesn't think the bot died
    await interaction.response.defer(thinking=True)

    # Prevent overlapping servo motions
    async with rescue_lock:
        loop = asyncio.get_running_loop()

        try:
            # Run the blocking GPIO/servo code off the event loop thread
            # If servo_rotate_once returns True/False, we capture it.
            result = await loop.run_in_executor(None, servo_rotate_once)
        except Exception as e:
            await interaction.followup.send(f"rescue failed: {type(e).__name__}: {e}")
            return

    # If your servo_rotate_once returns nothing, treat it as success
    if result is None or result is True:
        await interaction.followup.send("✅ rescue servo rotated once")
    else:
        await interaction.followup.send("⚠️ rescue servo reported failure")


@tree.command(name="exercise_finish", description="Mark finish of the current exercise (optional note).")
@app_commands.describe(note="e.g., duration, intensity")
async def exercise_finish_cmd(interaction: discord.Interaction, note: Optional[str] = None):
    global active_exercise
    append_event("exercise_finish", "finish", note=note or "")
    active_exercise = None
    await interaction.response.send_message("exercise finished")

@tree.command(name="exercise_brief", description="Log a brief, no-start/finish exercise note.")
@app_commands.describe(note="e.g., quick play, stairs")
async def exercise_brief_cmd(interaction: discord.Interaction, note: Optional[str] = None):
    append_event("exercise_brief", "brief", note=note or "")
    await interaction.response.send_message("exercise brief logged")


# slash command definition
@tree.command(name="feed", description="Dispense portions of food for Benny.")
@app_commands.describe(portions="Number of portions to dispense")
async def feed(interaction: discord.Interaction, portions: int = 1):
    await interaction.response.send_message(f"Feeding {portions} portion(s)...")

    loop = asyncio.get_running_loop()
    success = await loop.run_in_executor(None, dispense, portions)

    if success:
        await interaction.followup.send(f"✅ Dispensed {portions} portion(s).")
    else:
        await interaction.followup.send(f"⚠️ Feeder timed out before finishing.")

# you can add other commands later in the same way

# ---------- lifecycle ----------

@bot.event
async def on_ready():
    global watcher
    print(f"logged in as {bot.user} (latency ~{bot.latency:.3f}s)")
    try:
        watcher = LibreWatcher()
        print("[init] LibreWatcher ready")
    except Exception as e:
        print(f"[init] LibreWatcher failed: {e}")
    try:
        watcher = LibreWatcher()
        print("[init] LibreWatcher ready")
        warm_window_from_csv(watcher, WINDOW_MIN)   # optional, harmless if empty
    except Exception as e:
        print(f"[init] LibreWatcher failed: {e}")
    # background tasks
    bot.loop.create_task(poller())
    bot.loop.create_task(exercise_reminder_loop())
    # # slash sync
    # try:
    #     await tree.sync()
    #     print("slash commands synced")
    # except Exception as e:
    #     print(f"[sync] {e}")
# add this new hook (sync happens once, after commands are loaded)
@bot.event
async def setup_hook():
    global SYNCED_ONCE
    if SYNCED_ONCE:
        return
    try:
        synced = await tree.sync()
        print(f"[sync] global commands registered: {len(synced)}")
        for cmd in synced:
            print(f"  - /{cmd.name}")
    except Exception as e:
        print(f"[sync] {type(e).__name__}: {e}")
    SYNCED_ONCE = True


# add simple text fallbacks (no intents needed for slash; these still work with Intents.none)
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    content = message.content.strip()
    if content.lower().startswith("!last"):
        s = latest_snapshot or {}
        r = s.get("latest")
        if not r:
            await message.channel.send("no data yet")
            return
        avg = s.get("avg"); slope = s.get("slope")
        proj_low = s.get("proj_low"); proj_high = s.get("proj_high")
        loc = r.ts_utc.astimezone(TZ).isoformat()
        def fmt(x): return "—" if x is None else f"{x:.1f}"
        txt = (
            f"Last Reading: {r.mgdl:.0f} mg/dL\n"
            f"Local time: {loc}\n"
            f"Avg: {fmt(avg)}\n"
            f"Slope (mg/dL/min): {slope:.3f}\n"
            f"Proj {LOW_HORIZ_MIN}m: {fmt(proj_low)}\n"
            f"Proj {HIGH_HORIZ_MIN}m: {fmt(proj_high)}"
        )
        await message.channel.send(txt)
    elif content.lower().startswith("!graph"):
        parts = content.split()
        hours = 8
        if len(parts) >= 2:
            try: hours = max(1, min(48, int(parts[1])))
            except: pass
        buf = make_graph_png(hours)
        await message.channel.send(file=discord.File(buf, filename=f"glucose_{hours}h.png"))



if __name__ == "__main__":
    if not BOT_TOKEN or not LIBRE_USER or not LIBRE_PWD:
        print("set DISCORD_BOT_TOKEN, LIBRE_LINK_UP_USERNAME, LIBRE_LINK_UP_PASSWORD")
        raise SystemExit(2)
    # make sure events csv exists
    # ensure both CSVs have headers
    ensure_glucose_header()
    ensure_events_header()
    bot.run(BOT_TOKEN)
