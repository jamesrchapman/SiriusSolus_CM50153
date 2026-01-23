# libre_diag.py
import os, json, sys
from dotenv import load_dotenv
import src.solus.monkey_patch_librelinkup_tz as monkey_patch_librelinkup_tz  # patch first
from libre_link_up import LibreLinkUpClient

def j(obj): print(json.dumps(obj, indent=2)[:4000])  # safe-ish pretty print

def main():
    load_dotenv()
    url = os.getenv("LIBRE_LINK_UP_URL", "https://api.libreview.io")
    user = os.getenv("LIBRE_LINK_UP_USERNAME")
    pwd  = os.getenv("LIBRE_LINK_UP_PASSWORD")
    ver  = os.getenv("LIBRE_LINK_UP_VERSION", "4.16.0")
    if not (user and pwd):
        print("Set LIBRE_LINK_UP_USERNAME/PASSWORD")
        sys.exit(2)

    c = LibreLinkUpClient(username=user, password=pwd, url=url, version=ver)
    c.login()

    print("== /llu/connections ==")
    conns = c.get_connections() if hasattr(c, "get_connections") else c.get_raw_connections()
    # library versions differ; fallback if needed:
    if isinstance(conns, dict) and "data" in conns: conns = conns["data"]
    print(f"connections: {len(conns)}")
    j(conns[:2])

    print("\n== /llu/.../graph ==")
    raw = c.get_raw_graph_readings()
    print("top-level keys:", sorted(list(raw.keys())))
    gm = raw.get("glucoseMeasurement") or raw.get("glucoseItem")
    if gm:
        print("\nlatest object keys:", list(gm.keys()))
        j(gm)
    series = (raw.get("graphData") or raw.get("graphDataList") or raw.get("glucoseData") or raw.get("data") or [])
    print(f"\nseries length: {len(series)}")
    if series:
        print("last series item keys:", list(series[-1].keys()))
        j(series[-3:])  # last 3 points

if __name__ == "__main__":
    main()
