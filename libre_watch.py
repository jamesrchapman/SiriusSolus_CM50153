# libre_watch.py
# Poll LibreLinkUp, keep a rolling window, compute moving-average + slope,
# project forward, and send Discord alerts with cooldown.
#
# Dependencies:
#   pip install libre-link-up python-dateutil python-dotenv requests
#
# Usage examples:
#   python libre_watch.py --poll-sec 60 --window-min 20 ^
#       --low-threshold 100 --low-project-min 60 ^
#       --high-threshold 250 --high-project-min 30 ^
#       --cooldown-min 10 ^
#       --csv glucose_log.csv
#
# Discord webhook can be supplied via:
#   --discord-webhook https://discord.com/api/webhooks/...
# or env var DISCORD_WEBHOOK_URL

from __future__ import annotations
import os, csv, time, math, sys, json, signal, argparse
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Deque, Tuple, Optional

import requests
import monkey_patch_librelinkup_tz  # patch FIRST
from dotenv import load_dotenv
from libre_link_up import LibreLinkUpClient
from dateutil import parser as dtparser
from zoneinfo import ZoneInfo

# ---------- Data models ------------------------------------------------------

@dataclass
class Reading:
    ts_utc: datetime         # UTC timestamp
    mgdl: float              # glucose value
    source: str = "linkup"   # provenance

# ---------- Math helpers -----------------------------------------------------

def linear_regression_slope(points: list[Tuple[float, float]]) -> float:
    """
    Ordinary least squares slope (dy/dx) for points (x, y).
    Returns mg/dL per minute. Stable vs jitter; 0.0 if degenerate.
    """
    n = len(points)
    if n < 2:
        return 0.0
    sum_x = sum_y = sum_xx = sum_xy = 0.0
    for x, y in points:
        sum_x += x
        sum_y += y
        sum_xx += x * x
        sum_xy += x * y
    denom = n * sum_xx - sum_x * sum_x
    if abs(denom) < 1e-9:
        return 0.0
    return (n * sum_xy - sum_x * sum_y) / denom

# ---------- Rolling window ---------------------------------------------------

class RollingWindow:
    """
    Maintains a time-bounded window of readings (e.g., last 20 minutes)
    and exposes moving average + OLS slope over that window.
    """
    def __init__(self, window_minutes: int, tz_local: str):
        self.window_seconds = window_minutes * 60
        self.buf: Deque[Reading] = deque()
        self.local_tz = ZoneInfo(tz_local)

    def add(self, r: Reading) -> None:
        self.buf.append(r)
        self._trim()

    def _trim(self) -> None:
        if not self.buf:
            return
        newest_ts = self.buf[-1].ts_utc
        cutoff = newest_ts.timestamp() - self.window_seconds
        while self.buf and self.buf[0].ts_utc.timestamp() < cutoff:
            self.buf.popleft()

    def moving_average(self) -> Optional[float]:
        if not self.buf:
            return None
        return sum(r.mgdl for r in self.buf) / len(self.buf)

    def slope_mgdl_per_min(self) -> float:
        if len(self.buf) < 2:
            return 0.0
        latest_ts = self.buf[-1].ts_utc
        pts: list[Tuple[float, float]] = []
        # x-axis in minutes, latest ~ 0, older negative
        for r in self.buf:
            dt_min = (r.ts_utc - latest_ts).total_seconds() / 60.0
            pts.append((dt_min, r.mgdl))
        return linear_regression_slope(pts)

    def latest(self) -> Optional[Reading]:
        return self.buf[-1] if self.buf else None

    def size(self) -> int:
        return len(self.buf)

# ---------- Alerting (Discord + cooldown) -----------------------------------

class AlertManager:
    """
    Sends alerts with a cooldown (per alert "channel"—low vs high).
    Keeps last-sent times to avoid spam.
    """
    def __init__(self, webhook_url: Optional[str], cooldown_minutes: int):
        self.webhook = webhook_url
        self.cooldown = timedelta(minutes=cooldown_minutes)
        self._last_low: Optional[datetime]  = None
        self._last_high: Optional[datetime] = None

    def _can_fire(self, last: Optional[datetime]) -> bool:
        if last is None:
            return True
        return (datetime.now(timezone.utc) - last) >= self.cooldown

    def _post_discord(self, content: str, embed_fields: dict) -> None:
        # Fallback to console if no webhook configured
        if not self.webhook:
            print("\n" + "="*72)
            print(content)
            print(json.dumps(embed_fields, indent=2))
            print("="*72 + "\n")
            try:
                sys.stdout.write("\a"); sys.stdout.flush()
            except Exception:
                pass
            return

        payload = {
            "content": content,
            "embeds": [{
                "title": embed_fields.get("title", "Glucose Alert"),
                "description": embed_fields.get("description", ""),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "fields": [
                    {"name": k, "value": str(v), "inline": True}
                    for k, v in embed_fields.items()
                    if k not in ("title", "description")
                ]
            }]
        }
        try:
            r = requests.post(self.webhook, json=payload, timeout=10)
            if r.status_code >= 300:
                print(f"[warn] Discord webhook HTTP {r.status_code}: {r.text[:300]}")
        except Exception as e:
            print(f"[warn] Discord webhook failed: {e}")

    def alert_low(self, projected: float, latest: Reading, project_minutes: int,
                  avg: Optional[float], slope: float, local_tz: str) -> None:
        if not self._can_fire(self._last_low):
            return
        self._last_low = datetime.now(timezone.utc)
        loc = latest.ts_utc.astimezone(ZoneInfo(local_tz)).isoformat()
        content = f"⚠️ Projected LOW in {project_minutes}m: ~{projected:.1f} mg/dL"
        fields = {
            "title": "Projected Low",
            "Latest (mg/dL)": round(latest.mgdl, 1),
            "Moving Avg": None if avg is None else round(avg, 1),
            "Slope (mg/dL/min)": round(slope, 3),
            f"Proj {project_minutes}m": round(projected, 1),
            "Latest Time": loc,
        }
        self._post_discord(content, fields)

    def alert_high(self, projected: float, latest: Reading, project_minutes: int,
                   avg: Optional[float], slope: float, local_tz: str) -> None:
        if not self._can_fire(self._last_high):
            return
        self._last_high = datetime.now(timezone.utc)
        loc = latest.ts_utc.astimezone(ZoneInfo(local_tz)).isoformat()
        content = f"🚨 Projected HIGH in {project_minutes}m: ~{projected:.1f} mg/dL"
        fields = {
            "title": "Projected High",
            "Latest (mg/dL)": round(latest.mgdl, 1),
            "Moving Avg": None if avg is None else round(avg, 1),
            "Slope (mg/dL/min)": round(slope, 3),
            f"Proj {project_minutes}m": round(projected, 1),
            "Latest Time": loc,
        }
        self._post_discord(content, fields)

# ---------- Libre client wrapper --------------------------------------------

class LibreWatcher:
    """
    Wrap LibreLinkUpClient and provide a safe 'read_latest' API that
    returns a Reading(ts_utc, mgdl), handling various timestamp formats.
    """
    def __init__(self, url: str, username: str, password: str, app_version: str = "4.16.0"):
        self.client = LibreLinkUpClient(
            username=username,
            password=password,
            url=url,
            version=app_version,
        )
        self.client.login()

    def read_latest(self) -> Optional[Reading]:
        m = self.client.get_latest_reading()  # pydantic model
        data = m.model_dump(mode="json")
        val = (data.get("glucose_value_mgdl") or data.get("value_mgdl")
               or data.get("value") or data.get("ValueInMgPerDl"))
        ts = (data.get("timestamp_iso") or data.get("timestamp")
              or data.get("time") or data.get("Timestamp"))
        if val is None or ts is None:
            return None
        dt = _parse_to_utc(ts)  # defensive parse
        return Reading(ts_utc=dt, mgdl=float(val), source="linkup")

def _parse_to_utc(ts_any) -> datetime:
    if isinstance(ts_any, (int, float)):
        sec = ts_any / 1000.0 if ts_any > 1e12 else ts_any
        return datetime.fromtimestamp(sec, tz=timezone.utc)
    s = str(ts_any)
    try:
        dt = dtparser.isoparse(s)
    except Exception:
        dt = dtparser.parse(s, fuzzy=True)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

# ---------- CSV persistence --------------------------------------------------

class CsvSink:
    def __init__(self, path: str):
        self.path = path
        self._ensure_header()

    def _ensure_header(self) -> None:
        if not os.path.exists(self.path):
            with open(self.path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["ts_utc_iso", "mgdl", "source"])

    def append(self, r: Reading) -> None:
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([r.ts_utc.isoformat(), f"{r.mgdl:.2f}", r.source])

# ---------- Main loop --------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Libre trend watcher with projection alerts + Discord.")
    ap.add_argument("--window-min", type=int, default=20, help="Rolling window size in minutes.")
    ap.add_argument("--low-project-min", type=int, default=60, help="Projection horizon for LOW alert (minutes).")
    ap.add_argument("--low-threshold", type=float, default=100.0, help="Alert if projected (low horizon) < threshold.")
    ap.add_argument("--high-project-min", type=int, default=30, help="Projection horizon for HIGH alert (minutes).")
    ap.add_argument("--high-threshold", type=float, default=250.0, help="Alert if projected (high horizon) > threshold.")
    ap.add_argument("--cooldown-min", type=int, default=10, help="Cooldown between alerts of the same type (minutes).")
    ap.add_argument("--poll-sec", type=int, default=60, help="Polling interval seconds.")
    ap.add_argument("--csv", default="glucose_log.csv", help="CSV output path.")
    ap.add_argument("--local-tz", default=os.getenv("LOCAL_TZ", "America/Los_Angeles"),
                    help="Local timezone for printing only.")
    ap.add_argument("--discord-webhook", default=os.getenv("DISCORD_WEBHOOK_URL"),
                    help="Discord webhook URL (or set env DISCORD_WEBHOOK_URL).")
    args = ap.parse_args()

    load_dotenv()
    url = os.getenv("LIBRE_LINK_UP_URL", "https://api.libreview.io")
    user = os.getenv("LIBRE_LINK_UP_USERNAME")
    pwd  = os.getenv("LIBRE_LINK_UP_PASSWORD")
    ver  = os.getenv("LIBRE_LINK_UP_VERSION", "4.16.0")

    if not (user and pwd):
        print("Set LIBRE_LINK_UP_USERNAME and LIBRE_LINK_UP_PASSWORD (or use a .env).")
        sys.exit(2)

    watcher = LibreWatcher(url=url, username=user, password=pwd, app_version=ver)
    window = RollingWindow(window_minutes=args.window_min, tz_local=args.local_tz)
    sink = CsvSink(args.csv)
    alerts = AlertManager(webhook_url=args.discord_webhook, cooldown_minutes=args.cooldown_min)

    seen_ts: Optional[float] = None  # to avoid duplicate appends/prints

    def handle_sigint(sig, frame):
        print("\nbye.")
        sys.exit(0)
    signal.signal(signal.SIGINT, handle_sigint)

    while True:
        try:
            latest = watcher.read_latest()
            if latest is None:
                print("No reading yet.")
            else:
                ts_epoch = latest.ts_utc.timestamp()
                if seen_ts != ts_epoch:  # avoid duplicate processing if API repeats same reading
                    seen_ts = ts_epoch
                    window.add(latest)
                    sink.append(latest)

                    avg   = window.moving_average()
                    slope = window.slope_mgdl_per_min()

                    # Projections
                    proj_low  = None if avg is None else (avg + slope * args.low_project_min)
                    proj_high = None if avg is None else (avg + slope * args.high_project_min)

                    # Pretty status
                    loc = latest.ts_utc.astimezone(ZoneInfo(args.local_tz)).isoformat()
                    print(json.dumps({
                        "latest_mgdl": round(latest.mgdl, 1),
                        "latest_time_local": loc,
                        "window_points": window.size(),
                        "avg_mgdl": None if avg is None else round(avg, 1),
                        "slope_mgdl_per_min": round(slope, 3),
                        f"proj_{args.low_project_min}m": None if proj_low is None else round(proj_low, 1),
                        f"proj_{args.high_project_min}m": None if proj_high is None else round(proj_high, 1),
                    }, indent=2))

                    # Alerts with cooldown
                    if proj_low is not None and proj_low < args.low_threshold:
                        alerts.alert_low(proj_low, latest, args.low_project_min, avg, slope, args.local_tz)

                    if proj_high is not None and proj_high > args.high_threshold:
                        alerts.alert_high(proj_high, latest, args.high_project_min, avg, slope, args.local_tz)

            time.sleep(args.poll_sec)
        except Exception as e:
            print(f"[warn] {e.__class__.__name__}: {e}")
            time.sleep(args.poll_sec)

if __name__ == "__main__":
    main()
