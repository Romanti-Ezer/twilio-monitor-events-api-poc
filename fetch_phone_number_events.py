#!/usr/bin/env python3
"""
Fetch Twilio Monitor Events for phone numbers and export to CSV.

Usage:
    python fetch_phone_number_events.py                        (last 7 days)
    python fetch_phone_number_events.py --range month          (last 30 days)
    python fetch_phone_number_events.py --range week --output report.csv
"""

import argparse
import csv
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from twilio.rest import Client

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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


def parse_args():
    parser = argparse.ArgumentParser(description="Export Twilio phone-number Monitor Events to CSV")
    parser.add_argument(
        "--range",
        dest="date_range",
        choices=["week", "month"],
        default="week",
        help="Date range: 'week' (last 7 days) or 'month' (last 30 days). Default: week",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output CSV filename. Default: phone_number_events_<timestamp>.csv",
    )
    return parser.parse_args()


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


def main():
    args = parse_args()

    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not account_sid or not auth_token:
        print("ERROR: TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set.", file=sys.stderr)
        sys.exit(1)

    client = Client(account_sid, auth_token)
    start, end = build_date_range(args.date_range)

    print(f"Fetching phone-number events from {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')} ...")

    all_events = []
    for event_type in PHONE_NUMBER_EVENT_TYPES:
        print(f"  {event_type} ... ", end="", flush=True)
        events = [
            e for e in client.monitor.v1.events.list(
                event_type=event_type,
                start_date=start,
                end_date=end,
            )
            if e.resource_type == "phone-number"
        ]
        print(f"{len(events)} events")
        all_events.extend(events)

    all_events.sort(key=lambda e: str(e.event_date))

    output_file = args.output or f"phone_number_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    output_path = Path(output_file)

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for event in all_events:
            writer.writerow(event_to_row(event))

    print(f"\nDone. {len(all_events)} total events written to: {output_path}")


if __name__ == "__main__":
    main()
