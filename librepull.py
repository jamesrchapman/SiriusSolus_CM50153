# pull_latest.py
import monkey_patch_librelinkup_tz  # <-- import FIRST to apply the patch

from libre_link_up import LibreLinkUpClient
import os, json
from dotenv import load_dotenv
load_dotenv()

client = LibreLinkUpClient(
    username=os.environ["LIBRE_LINK_UP_USERNAME"],
    password=os.environ["LIBRE_LINK_UP_PASSWORD"],
    url=os.environ["LIBRE_LINK_UP_URL"],
    version=os.getenv("LIBRE_LINK_UP_VERSION", "4.16.0"),
    # country="America/Los_Angeles",   # your local tz
)
client.login()

# Latest reading for the first connection (you, if you’re the primary)
reading = client.get_latest_reading()
print(reading.model_dump_json(indent=2))
