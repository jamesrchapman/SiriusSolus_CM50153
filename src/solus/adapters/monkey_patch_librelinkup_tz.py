# monkey_patch_librelinkup_tz.py (v2)
from __future__ import annotations
import importlib, re
from datetime import datetime, timezone
from typing import Optional, Union
from dateutil import parser
from zoneinfo import ZoneInfo

TZ_GUESSES = {
    "US": ["America/Los_Angeles","America/Denver","America/Chicago","America/New_York","America/Phoenix","America/Anchorage","America/Honolulu"],
    "CA": ["America/Vancouver","America/Edmonton","America/Winnipeg","America/Toronto","America/Halifax"],
    "GB": ["Europe/London"], "UK": ["Europe/London"], "IE": ["Europe/Dublin"],
    "AU": ["Australia/Sydney","Australia/Melbourne","Australia/Brisbane","Australia/Perth"],
    "NZ": ["Pacific/Auckland"], "DE": ["Europe/Berlin"], "FR": ["Europe/Paris"],
    "ES": ["Europe/Madrid"], "IT": ["Europe/Rome"], "NL": ["Europe/Amsterdam"],
    "SE": ["Europe/Stockholm"], "NO": ["Europe/Oslo"], "DK": ["Europe/Copenhagen"],
    "FI": ["Europe/Helsinki"], "CH": ["Europe/Zurich"], "AT": ["Europe/Vienna"],
    "PL": ["Europe/Warsaw"], "IN": ["Asia/Kolkata"], "SG": ["Asia/Singapore"],
    "HK": ["Asia/Hong_Kong"], "JP": ["Asia/Tokyo"], "CN": ["Asia/Shanghai"],
}
LAST_RESORTS = ["America/Los_Angeles","America/New_York","Europe/London","UTC"]

def _parse_any(ts: Union[str, bytes, int, float]) -> datetime:
    # numeric epochs (seconds or ms)
    if isinstance(ts, (int, float)):
        sec = ts / 1000.0 if ts > 1e12 else ts
        return datetime.fromtimestamp(sec, tz=timezone.utc)

    if isinstance(ts, (bytes, bytearray)):
        ts = ts.decode(errors="ignore")
    s = str(ts).strip()

    # clean weird whitespace
    s = re.sub(r"\s+", " ", s)

    # try ISO first
    try:
        return parser.isoparse(s)
    except Exception:
        pass

    # try flexible parse (handles "11/4/2025 9:12 PM", etc.)
    try:
        return parser.parse(s, dayfirst=False, fuzzy=True)
    except Exception:
        # last chance: digits-only → maybe epoch
        digits = re.sub(r"[^\d]", "", s)
        if digits:
            n = int(digits)
            if n > 1e12: n //= 1000
            return datetime.fromtimestamp(n, tz=timezone.utc)
        raise

def _safe_convert_timestamp_string_to_unix(timestamp_string: str, country: Optional[str] = None, *_, **__) -> int:
    dt = _parse_any(timestamp_string)

    # If it already had tzinfo, normalize to UTC
    if dt.tzinfo is not None:
        return int(dt.astimezone(timezone.utc).timestamp())

    # No tz → attach best guess from country, else fallbacks, else UTC
    if country:
        for guess in TZ_GUESSES.get(str(country).upper(), []):
            try:
                return int(dt.replace(tzinfo=ZoneInfo(guess)).astimezone(timezone.utc).timestamp())
            except Exception:
                continue

    for guess in LAST_RESORTS:
        try:
            return int(dt.replace(tzinfo=ZoneInfo(guess)).astimezone(timezone.utc).timestamp())
        except Exception:
            pass

    return int(dt.replace(tzinfo=timezone.utc).timestamp())

def _apply_llu_patch() -> None:
    m = importlib.import_module("libre_link_up.client")
    # Primary name from your traceback:
    if hasattr(m, "_convert_timestamp_string_to_datetime"):
        setattr(m, "_convert_timestamp_string_to_datetime", _safe_convert_timestamp_string_to_unix)
    # Defensive aliases
    for name in ["convert_timestamp_string_to_datetime", "_convert_timestamp_to_unix", "_parse_timestamp"]:
        if hasattr(m, name):
            try:
                setattr(m, name, _safe_convert_timestamp_string_to_unix)
            except Exception:
                pass

_apply_llu_patch()
