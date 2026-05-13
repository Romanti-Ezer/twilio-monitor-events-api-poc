#!/usr/bin/env node
// Usage:
//   node fetch_phone_number_events.js          (last 7 days)
//   node fetch_phone_number_events.js month    (last 30 days)

const https = require("https");
const fs = require("fs");

const ACCOUNT_SID = process.env.TWILIO_ACCOUNT_SID;
const AUTH_TOKEN = process.env.TWILIO_AUTH_TOKEN;

const RANGE = process.argv[2] === "month" ? 30 : 7;
const EVENT_TYPES = ["phone-number.created", "phone-number.updated", "phone-number.deleted"];
const CSV_HEADER = "event_date,event_type,resource_sid,actor_sid,actor_type,source,source_ip_address,description";

// --- Date range ---
const now = new Date();
const start = new Date(now - RANGE * 24 * 60 * 60 * 1000);
const startDate = start.toISOString();
const endDate = now.toISOString();

// --- HTTP helper ---
function get(url) {
  return new Promise((resolve, reject) => {
    const auth = Buffer.from(`${ACCOUNT_SID}:${AUTH_TOKEN}`).toString("base64");
    https.get(url, { headers: { Authorization: `Basic ${auth}` } }, (res) => {
      let body = "";
      res.on("data", (chunk) => (body += chunk));
      res.on("end", () => resolve(JSON.parse(body)));
    }).on("error", reject);
  });
}

// --- Fetch all pages for one event type ---
async function fetchEvents(eventType) {
  const events = [];
  let url = `https://monitor.twilio.com/v1/Events?EventType=${eventType}&StartDate=${startDate}&EndDate=${endDate}&PageSize=1000`;

  while (url) {
    const data = await get(url);
    events.push(...(data.events || []));
    url = data.meta?.next_page_url || null;
  }
  return events;
}

// --- CSV row ---
function toRow(e) {
  const val = (v) => `"${(v || "").replace(/"/g, '""')}"`;
  return [e.event_date, e.event_type, e.resource_sid, e.actor_sid, e.actor_type, e.source, e.source_ip_address, e.description]
    .map(val).join(",");
}

// --- Main ---
async function main() {
  if (!ACCOUNT_SID || !AUTH_TOKEN) {
    console.error("Error: TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN must be set.");
    process.exit(1);
  }

  console.log(`Fetching phone-number events from ${startDate} to ${endDate} ...`);

  const allEvents = [];
  for (const eventType of EVENT_TYPES) {
    process.stdout.write(`  ${eventType} ... `);
    const events = await fetchEvents(eventType);
    console.log(`${events.length} events`);
    allEvents.push(...events);
  }

  allEvents.sort((a, b) => a.event_date.localeCompare(b.event_date));

  const output = `phone_number_events_${now.toISOString().replace(/[:.]/g, "-")}.csv`;
  const lines = [CSV_HEADER, ...allEvents.map(toRow)];
  fs.writeFileSync(output, lines.join("\n"));

  console.log(`\nDone. ${allEvents.length} total events written to: ${output}`);
}

main().catch((err) => { console.error(err); process.exit(1); });
