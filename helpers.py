from datetime import datetime, timedelta, timezone

PHONE_NUMBER_EVENT_TYPES = [
    "phone-number.created",
    "phone-number.updated",
    "phone-number.deleted",
]

CSV_FIELDS = [
    "event_date",
    "event_type",
    "resource_sid",
    "actor_sid",
    "actor_type",
    "source",
    "source_ip_address",
    "description",
]


def build_date_range(date_range: str):
    now = datetime.now(tz=timezone.utc)
    days = 7 if date_range == "week" else 30
    start = now - timedelta(days=days)
    return start, now


def event_to_row(event) -> dict:
    return {
        "event_date": event.event_date,
        "event_type": event.event_type,
        "resource_sid": event.resource_sid,
        "actor_sid": event.actor_sid,
        "actor_type": event.actor_type,
        "source": event.source,
        "source_ip_address": event.source_ip_address,
        "description": event.description or "",
    }
