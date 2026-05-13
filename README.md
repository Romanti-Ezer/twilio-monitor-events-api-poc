# Twilio Monitor Events — Phone Number Activity Report

> **Disclaimer:** This is sample code provided by Twilio Professional Services, built with AI assistance.
> It is intended as a starting point and proof of concept only. Test thoroughly in a lower environment
> and make appropriate improvements before using in production.

## How it works

The script queries the [Twilio Monitor Events API](https://www.twilio.com/docs/monitor/api) for three phone number lifecycle events:

- `phone-number.created` — a number was provisioned
- `phone-number.updated` — a number's configuration changed
- `phone-number.deleted` — a number was released

Because Monitor Events only include the phone number SID (e.g. `PNxxx`) and not the E.164 number, the script maintains a persistent local map (`output/phone_number_map.json`) that resolves SIDs to phone numbers. On each run it:

1. Loads the existing map from disk (preserving history of deleted numbers)
2. Refreshes all active numbers from the [IncomingPhoneNumbers API](https://www.twilio.com/docs/phone-numbers/api/incomingphonenumber-resource)
3. Fetches the requested events and resolves any unknown SIDs individually
4. Saves the updated map and writes a timestamped CSV to `output/`

> **Note on deleted numbers:** Once a number is released from an account, Twilio's API no longer returns it.
> Numbers seen by this script before deletion will be preserved in the map file. Numbers deleted before
> the script was ever run will appear as `[DELETED]` in the report.

> **Data retention:** Monitor Events are retained for 30 days on standard accounts and up to 13 months
> on Enterprise/Security Edition accounts.

## Requirements

- Python 3.9+
- A Twilio account with Monitor Events enabled

Install dependencies:

```bash
pip install -r requirements.txt
```

Set credentials — copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

The script supports two authentication methods:

**Option 1 — API Key (recommended for automation)**  
API Keys are scoped and revocable without affecting other integrations. Create one at [twilio.com/console/project/api-keys](https://www.twilio.com/console/project/api-keys).

```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_KEY=SKxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_API_SECRET=your_api_secret_here
```

**Option 2 — Auth Token (quick local testing only)**  
The master Auth Token grants full account access. Avoid using it in automated environments.

```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
```

## Usage

```bash
# Last 7 days (default)
python fetch_phone_number_events.py

# Last 30 days
python fetch_phone_number_events.py --range month

# Custom output filename
python fetch_phone_number_events.py --range week --output output/my_report.csv
```

Output CSV is written to `output/phone_number_events_<timestamp>.csv` with columns:

`event_date`, `event_type`, `phone_number`, `resource_sid`, `actor_sid`, `actor_type`, `source`, `source_ip_address`, `description`

## Automation

### Linux / macOS — cron

Run weekly every Monday at 8am:

```bash
crontab -e
# Add:
0 8 * * 1 /usr/bin/python3 /path/to/fetch_phone_number_events.py --range week
```

### Windows — Task Scheduler

Create a Basic Task in Task Scheduler pointing to `python fetch_phone_number_events.py --range week`, triggered weekly.

### GitHub Actions

```yaml
on:
  schedule:
    - cron: "0 8 * * 1"  # Every Monday at 8am UTC
jobs:
  report:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install -r requirements.txt
      - run: python fetch_phone_number_events.py --range week
        env:
          TWILIO_ACCOUNT_SID: ${{ secrets.TWILIO_ACCOUNT_SID }}
          TWILIO_API_KEY: ${{ secrets.TWILIO_API_KEY }}
          TWILIO_API_SECRET: ${{ secrets.TWILIO_API_SECRET }}
      - uses: actions/upload-artifact@v4
        with:
          name: phone-number-report
          path: output/*.csv
```

## Files

| File | Description |
|------|-------------|
| `fetch_phone_number_events.py` | Main script — run this |
| `helpers.py` | Supporting utilities (date range, map I/O, CSV helpers) |
| `requirements.txt` | Python dependencies |
| `.env.example` | Credential template — copy to `.env` |
| `phone_number_map.example.json` | Example of the SID → E.164 map format maintained in `output/` |

## References

- [Twilio Monitor Events API](https://www.twilio.com/docs/monitor/api)
- [IncomingPhoneNumbers API](https://www.twilio.com/docs/phone-numbers/api/incomingphonenumber-resource)
- [Twilio Python SDK](https://www.twilio.com/docs/libraries/python)
