"""
benny_api.py

FastAPI backend that replaces the Discord bot layer.

Responsibilities:
- Poll LibreLinkUp regularly using your existing LibreWatcher design.
- Store latest snapshot (current reading, avg, slope, projections).
- Serve CGM summary for the watch (current + history + prediction).
- Trigger feeder (feed/rescue) via feeder_control.dispense.
"""

from __future__ import annotations

import os
import csv
import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional, Deque, List
from collections import deque

from fastapi import FastAPI, HTTPException, Depends, Header
from pydantic import BaseModel, Field

# Your existing imports
import src.solus.monkey_patch_librelinkup_tz as monkey_patch_librelinkup_tz  # must be first
from dotenv import load_dotenv
from zoneinfo import ZoneInfo
from libre_link_up import LibreLinkUpClient
from src.solus.feeder_control import dispense  # your motor function

# ============================ LOAD CONFIG ====================================

load_dotenv()

LIBRE_USER        = os.getenv("LIBRE_LINK_UP_USERNAME", "")
LIBRE_PWD         = os.getenv("LIBRE_LINK_UP_PASSWORD", "")
LIBRE_URL         = os.getenv("LIBRE_LINK_UP_URL", "https://api.libreview.io")
LIBRE_VER         = os.getenv("LIBRE_LINK_UP_VERSION", "4.16.0")
LOCAL_TZ_NAME     = os.getenv("LOCAL_TZ", "America/Los_Angeles")

POLL_SEC          = int(os.getenv("POLL_SEC", "60"))
WINDOW_MIN        = int(os.getenv("WINDOW_MIN", "20"))
LOW_HORIZ_MIN     = int(os.getenv("LOW_HORIZ_MIN", "60"))
HIGH_HORIZ_MIN    = int(os.getenv("HIGH_HORIZ_MIN", "30"))

GLUCOSE_CSV       = os.getenv("GLUCOSE_CSV", "glucose_log.csv")

WATCH_API_TOKEN   = os.getenv("WATCH_API_TOKEN")
if not WATCH_API_TOKEN:
    raise RuntimeError("WATCH_API_TOKEN must be set in environment.")

TZ = ZoneInfo(LOCAL_TZ_NAME)

# Time windows for watch summary
HISTORY_WINDOW_MIN      = 480   # last 8 hours
PREDICTION_HORIZON_MIN  = 60    # next 1 hour
PREDICTION_STEP_MIN     = 5     # 5-minute prediction resolution


# ============================ BASIC UTILS ====================================

def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def parse_iso_utc(s: str) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


# ============================ GLUCOSE CSV ====================================

def ensure_glucose_header():
    """Create glucose CSV with header if missing."""
    if not os.path.exists(GLUCOSE_CSV):
        with open(GLUCOSE_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["ts_utc_iso", "mgdl", "source"])


@dataclass
class Reading:
    ts_utc: datetime
    mgdl: float


def append_glucose_row(r: Reading, source: str = "linkup") -> None:
    """Append one glucose row to CSV."""
    with open(GLUCOSE_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([r.ts_utc.isoformat(), f"{r.mgdl:.2f}", source])


def read_glucose_csv_last_hours(hours: int) -> List[Reading]:
    """Read last N hours from glucose_log.csv."""
    out: List[Reading] = []
    if not os.path.exists(GLUCOSE_CSV):
        return out
    cutoff = now_utc().timestamp() - hours * 3600
    with open(GLUCOSE_CSV, "r", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for row in rd:
            ts = parse_iso_utc(row.get("ts_utc_iso", ""))
            try:
                mg = float(row.get("mgdl", ""))
            except Exception:
                continue
            if not ts:
                continue
            if ts.timestamp() >= cutoff:
                out.append(Reading(ts, mg))
    return out


def warm_window_from_csv(window: "RollingWindow", minutes: int):
    """Prime the rolling window with recent CSV data."""
    cutoff = now_utc().timestamp() - minutes * 60
    if not os.path.exists(GLUCOSE_CSV):
        return
    try:
        with open(GLUCOSE_CSV, "r", encoding="utf-8") as f:
            rd = csv.DictReader(f)
            rows = [row for row in rd if row.get("ts_utc_iso") and row.get("mgdl")]
        recent: List[Reading] = []
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
        recent.sort(key=lambda x: x.ts_utc)
        for r in recent:
            window.add(r)
        if recent:
            print(f"[warm] window primed with {len(recent)} points")
    except Exception as e:
        print(f"[warm] {type(e).__name__}: {e}")


# ============================ ROLLING WINDOW =================================

class RollingWindow:
    """Rolling time window for average/slope, same logic you already use."""

    def __init__(self, window_minutes: int):
        self.window_sec = window_minutes * 60
        self.buf: Deque[Reading] = deque()

    def add(self, r: Reading):
        self.buf.append(r)
        cutoff = r.ts_utc.timestamp() - self.window_sec
        while self.buf and self.buf[0].ts_utc.timestamp() < cutoff:
            self.buf.popleft()

    def avg(self) -> Optional[float]:
        if not self.buf:
            return None
        return sum(r.mgdl for r in self.buf) / len(self.buf)

    def slope(self) -> float:
        """Return slope in mg/dL per minute."""
        if len(self.buf) < 2:
            return 0.0
        latest = self.buf[-1].ts_utc
        sx = sy = sxx = sxy = 0.0
        n = 0
        for r in self.buf:
            x = (r.ts_utc - latest).total_seconds() / 60.0
            y = r.mgdl
            sx += x; sy += y; sxx += x * x; sxy += x * y; n += 1
        denom = n * sxx - sx * sx
        if abs(denom) < 1e-12:
            return 0.0
        return (n * sxy - sx * sy) / denom


# ============================ LIBRE WATCHER ==================================

class LibreWatcher:
    """
    Polls LibreLinkUp and maintains:
    - latest Reading
    - rolling window stats
    """

    def __init__(self):
        self.client = LibreLinkUpClient(
            username=LIBRE_USER,
            password=LIBRE_PWD,
            url=LIBRE_URL,
            version=LIBRE_VER
        )
        self.client.login()
        self.window = RollingWindow(WINDOW_MIN)
        self._seen_unix: Optional[float] = None
        self.latest: Optional[Reading] = None

        # Prime from CSV if available
        warm_window_from_csv(self.window, WINDOW_MIN)

    def fetch_once(self) -> Optional[Reading]:
        m = self.client.get_latest_reading()
        d = m.model_dump(mode="json")

        val = (
            d.get("value_in_mg_per_dl")
            or d.get("glucose_value_mgdl")
            or d.get("value_mgdl")
            or d.get("value")
        )
        ts = (
            d.get("unix_timestamp")
            or d.get("timestamp_iso")
            or d.get("timestamp")
            or d.get("time")
        )

        if val is None or ts is None:
            return None

        if isinstance(ts, (int, float)):
            # ms vs s
            sec = ts / 1000.0 if ts > 1e12 else ts
            dt = datetime.fromtimestamp(sec, tz=timezone.utc)
        else:
            dt = parse_iso_utc(str(ts)) or now_utc()

        return Reading(dt, float(val))

    def tick(self) -> dict:
        """
        One polling step:
        - Fetch new reading.
        - If it's a new timestamp, update window, CSV, latest.
        - Return summary dict (current, avg, slope, projections).
        """
        r = self.fetch_once()
        if r:
            u = r.ts_utc.timestamp()
            if self._seen_unix != u:
                self._seen_unix = u
                self.window.add(r)
                self.latest = r
                try:
                    append_glucose_row(r, source="linkup")
                except Exception as e:
                    print(f"[persist] {type(e).__name__}: {e}")

        avg = self.window.avg()
        slope = self.window.slope()
        proj_low = None if avg is None else avg + slope * LOW_HORIZ_MIN
        proj_high = None if avg is None else avg + slope * HIGH_HORIZ_MIN

        return {
            "latest": self.latest,
            "avg": avg,
            "slope": slope,             # mg/dL per minute
            "proj_low": proj_low,
            "proj_high": proj_high,
        }


# Global watcher and latest snapshot (shared with API)
watcher: Optional[LibreWatcher] = None
latest_snapshot: Optional[dict] = None


async def poll_loop():
    """Background task: poll LibreLinkUp periodically and update snapshot."""
    global watcher, latest_snapshot
    last_seen = None
    while True:
        try:
            if watcher:
                snap = watcher.tick()
                if snap:
                    latest_snapshot = snap
                    r: Optional[Reading] = snap.get("latest")
                    if r:
                        ts = r.ts_utc.timestamp()
                        if ts != last_seen:
                            last_seen = ts
                            print(f"[poll] {r.ts_utc.astimezone(TZ).isoformat()}  {r.mgdl:.0f} mg/dL")
        except Exception as e:
            print(f"[poll] {type(e).__name__}: {e}")
        await asyncio.sleep(POLL_SEC)


# ============================ FEEDER CONTROLLER ==============================

@dataclass
class FeedEvent:
    timestamp: datetime
    portions: int
    success: bool
    reason: Optional[str] = None


@dataclass
class RescueEvent:
    timestamp: datetime
    success: bool
    reason: Optional[str] = None


class FeederController:
    """
    Wraps feeder_control.dispense and enforces simple lockouts.
    """

    def __init__(self):
        self._last_feed: Optional[FeedEvent] = None
        self._last_rescue: Optional[RescueEvent] = None
        self._lockout_until: Optional[datetime] = None

        self.max_portions_per_feed = 4
        self.feed_lockout_minutes = 5
        self.rescue_lockout_minutes = 45

    def _now(self) -> datetime:
        return now_utc()

    def get_status(self):
        return {
            "last_feed": self._last_feed,
            "last_rescue": self._last_rescue,
            "lockout_until": self._lockout_until,
        }

    def request_feed(self, portions: int) -> FeedEvent:
        now = self._now()

        if portions <= 0:
            return FeedEvent(now, portions, False, "Portions must be positive.")

        if portions > self.max_portions_per_feed:
            return FeedEvent(
                now,
                portions,
                False,
                f"Max {self.max_portions_per_feed} portions per feed.",
            )

        if self._lockout_until and now < self._lockout_until:
            return FeedEvent(
                now,
                portions,
                False,
                f"Feed locked out until {self._lockout_until.isoformat()}",
            )

        # Run your blocking dispense() in-place here.
        # If you want, later, you can move this into a thread pool.
        try:
            success = bool(dispense(portions))
            reason = None if success else "dispense() reported failure"
        except Exception as e:
            success = False
            reason = f"{type(e).__name__}: {e}"

        event = FeedEvent(now, portions, success, reason)
        self._last_feed = event

        # Set lockout (even if failure, so you don't hammer hardware)
        self._lockout_until = now + timedelta(minutes=self.feed_lockout_minutes)
        return event

    def request_rescue(self) -> RescueEvent:
        now = self._now()

        if self._lockout_until and now < self._lockout_until:
            return RescueEvent(
                now,
                False,
                f"Rescue locked out until {self._lockout_until.isoformat()}",
            )

        # TODO: wire to actual rescue action if you have one.
        success = True
        reason = None

        event = RescueEvent(now, success, reason)
        self._last_rescue = event

        self._lockout_until = now + timedelta(minutes=self.rescue_lockout_minutes)
        return event


feeder = FeederController()


# ============================ API MODELS =====================================

class CgmPointModel(BaseModel):
    t: str
    mgdl: float


class CgmCurrentModel(BaseModel):
    mgdl: float
    timestamp_utc: str
    trend: Optional[str]
    delta_15min: Optional[float]


class CgmHistoryModel(BaseModel):
    window_minutes: int
    points: List[CgmPointModel]


class CgmPredictionModel(BaseModel):
    horizon_minutes: int
    points: List[CgmPointModel]


class CgmFlagsModel(BaseModel):
    is_sensor_stale: bool
    minutes_since_last_reading: Optional[int]
    low_alert: bool
    high_alert: bool


class CgmSummaryModel(BaseModel):
    current: Optional[CgmCurrentModel]
    history: CgmHistoryModel
    prediction: CgmPredictionModel
    flags: CgmFlagsModel


class FeedRequestModel(BaseModel):
    portions: int = Field(..., ge=1, le=10)


class FeedResponseModel(BaseModel):
    accepted: bool
    portions: int
    executed: bool
    executed_at_utc: Optional[str]
    reason: Optional[str]
    lockout_until_utc: Optional[str]


class RescueResponseModel(BaseModel):
    accepted: bool
    executed: bool
    executed_at_utc: Optional[str]
    reason: Optional[str]
    lockout_until_utc: Optional[str]


class FeederStatusModel(BaseModel):
    last_feed_at_utc: Optional[str]
    last_feed_portions: Optional[int]
    last_rescue_at_utc: Optional[str]
    lockout_until_utc: Optional[str]


# ============================ AUTH DEPENDENCY ================================

def verify_token(x_watch_token: str = Header(default=None)) -> None:
    if x_watch_token is None:
        raise HTTPException(status_code=401, detail="Missing X-Watch-Token header.")
    if x_watch_token != WATCH_API_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid token.")


# ============================ FASTAPI APP ====================================

app = FastAPI(title="Benny Backend")


@app.on_event("startup")
async def startup_event():
    global watcher
    ensure_glucose_header()
    if not LIBRE_USER or not LIBRE_PWD:
        print("Libre credentials not set; watcher will not start.")
        watcher = None
    else:
        try:
            watcher = LibreWatcher()
            print("[init] LibreWatcher ready")
        except Exception as e:
            watcher = None
            print(f"[init] LibreWatcher failed: {e}")

    # start polling loop
    asyncio.create_task(poll_loop())


@app.get("/health")
def health():
    return {"status": "ok", "time": now_utc().isoformat()}


@app.get("/cgm/summary", response_model=CgmSummaryModel)
def get_cgm_summary(_: None = Depends(verify_token)) -> CgmSummaryModel:
    """Return current BG, last 8h history, and simple 1h linear prediction."""

    s = latest_snapshot or {}
    r: Optional[Reading] = s.get("latest")

    # Build current
    current_model: Optional[CgmCurrentModel] = None
    minutes_since_last = None
    is_stale = True
    low_alert = False
    high_alert = False
    trend: Optional[str] = None
    delta_15: Optional[float] = None

    now = now_utc()

    if r:
        delta = now - r.ts_utc
        minutes_since_last = int(delta.total_seconds() // 60)
        is_stale = minutes_since_last > 10

        mgdl = r.mgdl
        low_alert = mgdl < 70.0
        high_alert = mgdl > 250.0

        # trend & delta_15 based on slope (mg/dL per minute)
        slope = float(s.get("slope") or 0.0)
        delta_15 = slope * 15.0
        if delta_15 > 5:
            trend = "rapid_rise"
        elif delta_15 > 1:
            trend = "rising"
        elif delta_15 < -5:
            trend = "rapid_fall"
        elif delta_15 < -1:
            trend = "falling"
        else:
            trend = "flat"

        current_model = CgmCurrentModel(
            mgdl=mgdl,
            timestamp_utc=r.ts_utc.isoformat(),
            trend=trend,
            delta_15min=delta_15,
        )

    # History: from CSV, last 8h, downsample by picking every Nth point if needed
    raw_hist = read_glucose_csv_last_hours(HISTORY_WINDOW_MIN // 60)
    history_points: List[CgmPointModel] = []

    # naive downsample: target <= 96 points (one every 5 minutes)
    max_points = 96
    step = max(1, len(raw_hist) // max_points) if raw_hist else 1

    for i, reading in enumerate(raw_hist):
        if i % step != 0:
            continue
        history_points.append(
            CgmPointModel(t=reading.ts_utc.isoformat(), mgdl=reading.mgdl)
        )

    history_model = CgmHistoryModel(
        window_minutes=HISTORY_WINDOW_MIN,
        points=history_points
    )

    # Prediction: simple linear projection from latest using slope
    pred_points: List[CgmPointModel] = []
    if r:
        slope = float(s.get("slope") or 0.0)  # mg/dL per minute
        base = r.mgdl
        for mins in range(PREDICTION_STEP_MIN,
                          PREDICTION_HORIZON_MIN + 1,
                          PREDICTION_STEP_MIN):
            t = r.ts_utc + timedelta(minutes=mins)
            mg = base + slope * mins
            pred_points.append(
                CgmPointModel(t=t.isoformat(), mgdl=mg)
            )

    prediction_model = CgmPredictionModel(
        horizon_minutes=PREDICTION_HORIZON_MIN,
        points=pred_points
    )

    flags_model = CgmFlagsModel(
        is_sensor_stale=is_stale,
        minutes_since_last_reading=minutes_since_last,
        low_alert=low_alert,
        high_alert=high_alert,
    )

    return CgmSummaryModel(
        current=current_model,
        history=history_model,
        prediction=prediction_model,
        flags=flags_model,
    )


@app.post("/feeder/feed", response_model=FeedResponseModel)
def post_feed(request: FeedRequestModel, _: None = Depends(verify_token)) -> FeedResponseModel:
    event = feeder.request_feed(request.portions)
    status = feeder.get_status()

    lockout_until = status["lockout_until"]
    lockout_str = lockout_until.isoformat() if lockout_until else None

    accepted = event.reason is None or event.success

    return FeedResponseModel(
        accepted=accepted,
        portions=event.portions,
        executed=event.success,
        executed_at_utc=event.timestamp.isoformat() if event.success else None,
        reason=event.reason,
        lockout_until_utc=lockout_str,
    )


@app.post("/feeder/rescue", response_model=RescueResponseModel)
def post_rescue(_: None = Depends(verify_token)) -> RescueResponseModel:
    event = feeder.request_rescue()
    status = feeder.get_status()

    lockout_until = status["lockout_until"]
    lockout_str = lockout_until.isoformat() if lockout_until else None

    accepted = event.reason is None or event.success

    return RescueResponseModel(
        accepted=accepted,
        executed=event.success,
        executed_at_utc=event.timestamp.isoformat() if event.success else None,
        reason=event.reason,
        lockout_until_utc=lockout_str,
    )


@app.get("/feeder/status", response_model=FeederStatusModel)
def get_feeder_status(_: None = Depends(verify_token)) -> FeederStatusModel:
    s = feeder.get_status()

    last_feed: Optional[FeedEvent] = s["last_feed"]
    last_rescue: Optional[RescueEvent] = s["last_rescue"]
    lockout_until: Optional[datetime] = s["lockout_until"]

    return FeederStatusModel(
        last_feed_at_utc=last_feed.timestamp.isoformat() if last_feed else None,
        last_feed_portions=last_feed.portions if last_feed else None,
        last_rescue_at_utc=last_rescue.timestamp.isoformat() if last_rescue else None,
        lockout_until_utc=lockout_until.isoformat() if lockout_until else None,
    )
