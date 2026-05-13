#!/usr/bin/env python3
"""
Fetch Twilio Monitor Events for phone numbers and export to CSV.

Usage:
    python fetch_phone_number_events.py --range week
    python fetch_phone_number_events.py --range month
    python fetch_phone_number_events.py --range week --output my_report.csv
"""

import argparse
import csv
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional if env vars are already set

MONITOR_EVENTS_URL = "https://monitor.twilio.com/v1/Events"
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
        help="Date range to fetch: 'week' (last 7 days) or 'month' (last 30 days). Default: week",
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
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return start.strftime(fmt), now.strftime(fmt)


def fetch_events_for_type(event_type: str, start_date: str, end_date: str, auth: HTTPBasicAuth) -> list[dict]:
    events = []
    url = MONITOR_EVENTS_URL
    params = {
        "EventType": event_type,
        "StartDate": start_date,
        "EndDate": end_date,
        "PageSize": 1000,
    }

    while url:
        response = requests.get(url, auth=auth, params=params, timeout=30)
        if response.status_code != 200:
            print(f"  ERROR {response.status_code}: {response.text}", file=sys.stderr)
            response.raise_for_status()

        payload = response.json()
        page_events = [
            e for e in payload.get("events", [])
            if e.get("resource_type") == "phone-number"
        ]
        events.extend(page_events)

        # After first request, params are encoded in next_page_url
        params = {}
        url = payload.get("meta", {}).get("next_page_url") or payload.get("next_page_url")

    return events


def event_to_row(event: dict) -> dict:
    return {
        "event_date": event.get("event_date", ""),
        "event_type": event.get("event_type", ""),
        "resource_sid": event.get("resource_sid", ""),
        "actor_sid": event.get("actor_sid", ""),
        "actor_type": event.get("actor_type", ""),
        "source": event.get("source", ""),
        "source_ip_address": event.get("source_ip_address", ""),
        "description": event.get("description", ""),
    }


def main():
    args = parse_args()

    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not account_sid or not auth_token:
        print("ERROR: TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set (in .env or environment).", file=sys.stderr)
        sys.exit(1)

    auth = HTTPBasicAuth(account_sid, auth_token)
    start_date, end_date = build_date_range(args.date_range)

    print(f"Fetching phone-number events from {start_date} to {end_date} ...")

    all_events = []
    for event_type in PHONE_NUMBER_EVENT_TYPES:
        print(f"  {event_type} ... ", end="", flush=True)
        events = fetch_events_for_type(event_type, start_date, end_date, auth)
        print(f"{len(events)} events")
        all_events.extend(events)

    # Sort chronologically
    all_events.sort(key=lambda e: e.get("event_date", ""))

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
