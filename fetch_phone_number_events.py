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
from datetime import datetime
from pathlib import Path

from twilio.rest import Client

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from helpers import (
    PHONE_NUMBER_EVENT_TYPES, CSV_FIELDS,
    build_date_range, load_map, save_map, refresh_map_from_api,
    resolve_number, event_to_row,
)


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


def main():
    args = parse_args()

    # Load credentials
    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    if not account_sid or not auth_token:
        print("ERROR: TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set.", file=sys.stderr)
        sys.exit(1)

    # Set up Twilio client and date range
    client = Client(account_sid, auth_token)
    start, end = build_date_range(args.date_range)

    # Ensure output directory exists
    Path("output").mkdir(exist_ok=True)

    # Load persistent SID → phone_number map and refresh with all active numbers
    number_map = load_map()
    print("Refreshing phone number map from API ...")
    refresh_map_from_api(client, number_map)

    # Fetch events for each event type
    print(f"\nFetching phone-number events from {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')} ...")
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

    # Resolve any SIDs not already in the map (e.g. numbers deleted before first run)
    for event in all_events:
        resolve_number(client, event.resource_sid, number_map)

    # Save updated map back to disk
    save_map(number_map)

    # Sort chronologically and write to CSV
    all_events.sort(key=lambda e: str(e.event_date))

    output_path = Path(args.output or f"output/phone_number_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for event in all_events:
            writer.writerow(event_to_row(event, number_map))

    print(f"\nDone. {len(all_events)} total events written to: {output_path}")


if __name__ == "__main__":
    main()
