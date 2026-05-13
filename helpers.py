import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

PHONE_NUMBER_EVENT_TYPES = [
    "phone-number.created",
    "phone-number.updated",
    "phone-number.deleted",
]

CSV_FIELDS = [
    "event_date",
    "event_type",
    "phone_number",
    "resource_sid",
    "actor_sid",
    "actor_type",
    "source",
    "source_ip_address",
    "description",
]

MAP_FILE = "phone_number_map.json"


def build_date_range(date_range: str):
    now = datetime.now(tz=timezone.utc)
    days = 7 if date_range == "week" else 30
    start = now - timedelta(days=days)
    return start, now


def load_map(path=MAP_FILE) -> dict:
    p = Path(path)
    if p.exists():
        return json.loads(p.read_text())
    return {}


def save_map(number_map: dict, path=MAP_FILE):
    Path(path).write_text(json.dumps(number_map, indent=2))


def refresh_map_from_api(client, number_map: dict):
    """Bulk-fetch all active IncomingPhoneNumbers and merge into the map.
    Existing entries (including deleted numbers) are preserved."""
    page = client.incoming_phone_numbers.list(page_size=1000)
    count = 0
    for record in page:
        number_map[record.sid] = record.phone_number
        count += 1
    print(f"  {count} active numbers loaded into map")


def resolve_number(client, sid: str, number_map: dict) -> str:
    """Return the E.164 number for a SID, fetching individually if not in map."""
    if sid in number_map:
        return number_map[sid]
    try:
        phone_number = client.incoming_phone_numbers(sid).fetch().phone_number
    except Exception:
        phone_number = "[DELETED]"
    number_map[sid] = phone_number
    return phone_number


def event_to_row(event, number_map: dict) -> dict:
    return {
        "event_date": event.event_date,
        "event_type": event.event_type,
        "phone_number": number_map.get(event.resource_sid, "[DELETED]"),
        "resource_sid": event.resource_sid,
        "actor_sid": event.actor_sid,
        "actor_type": event.actor_type,
        "source": event.source,
        "source_ip_address": event.source_ip_address,
        "description": event.description or "",
    }
