# Public StillPoint Calendar browser — first usable interface

**Status:** public-source, static-site implementation and build path. This
document does **not** assert that the site has been deployed at a public URL,
that the private RobertOS/StillPointOS integrations passed, or that a native
Apple Watch binary has been qualified.

## What people can do

A mobile-friendly calendar interface lets a person enter an ordinary Gregorian
date and explore the corresponding published StillPoint Common Calendar day.
It displays the Common year/month/day and weekday, week-of-year, sacred-source
overlay, selected Jubilee coordinate, observances, and the full seven-day
Common week with a clickable day selector. Previous/next buttons navigate
the external ordinary-date sequence, including a Common-year boundary.

This is a *read-only consumer*. It does not request login, run an AI model,
write company state, call a paid service, use personal location, or ask for a
payment method.

## Why this is not a second calendar engine

The static exporter (tools/export_public_calendar_site.py) calls the existing
Python Core calendar_day_payload() separately for **all 18,200 published days**,
and saves only selected consumer fields.

- The public browser reads those verified, precomputed Core outputs.
- The browser performs no sacred-calendar, Jubilee, observance, Common-week,
  or Common-date calculations of its own. It selects records by their exact
  Gregorian external translation labels, and displays the Core-computed week.
- Each of 50 annual shards has 364 records. A small index records year ranges,
  publication digest, record counts, and per-shard SHA-256 fingerprints.
- The full export must have Common years 2026–2075. Nothing can issue
  Common 2076 through a date picker, despite its separate mathematical status.
- Civil dusk and sacred sunset are described but **not presented as actual
  location-specific sunrise/sunset instants**.

The March 25 schematic sacred-source year anchor and the 2027 Jubilee epoch
with overlapping 49-year cycles retain their already-selected versioned
interpretive status. This interface neither enacts civil authority nor claims
that a religious practice is compulsory for all communities.

## Build the working site from the public source

From the current **public Canonical Core** checkout:

~~~sh
python -m pip install .
python tools/export_public_calendar_site.py --output /tmp/stillpoint-public-browser
cd /tmp/stillpoint-public-browser
python -m http.server 8000
~~~

Then open http://localhost:8000/ in a browser. This is a local demonstration
until deployment to a publicly reachable static host is explicitly configured.
The browser fetches ./data/index.json and one 364-day year shard at a time.
It needs a static HTTP server; opening the HTML directly as a local file may
block JSON requests under normal browser security rules.

No third-party JavaScript libraries, paid backend, telemetry, account,
location permissions or credentials are required.

## Testing

~~~sh
python -m unittest discover -s tests/calendar_core -p 'test_public_calendar_site_export.py' -v
python tools/export_public_calendar_site.py --output /tmp/stillpoint-public-browser
~~~

The site tests create a bounded three-year test export (2026, 2027, 2075),
validate SHA-256 digests and exact Core provenance, and assert the 2026/2027
364-day rollover and published last day. The production build emits **50**
separate year shards, all 18,200 selected public records, and a manifest
marking the complete publication. Incomplete test fixtures must not be
misrepresented as public production data.

The public-calendar-browser workflow runs these checks and builds the full
static site on GitHub's **existing public standard Ubuntu runner**.
It does not deploy the site, change Pages settings, or upload private artifacts.

## Publication milestone, still separate

After a green browser build, choose an available **free** static publishing
path within the existing public repository (for example GitHub Pages after
verifying it is configured), review the generated output and accessibility,
and verify the actual public URL on desktop and mobile. Do not assert a
deployed public website until its URL is independently reachable.

## Scope that remains intentionally unfinished

- The public browser is not a full autonomous assistant.
- The private RobertOS/StillPointOS code and source history stay private.
- Private runner admission failures and exact-current-head integration
  qualification remain a distinct issue.
- Apple Watch CI and device deployment need their own verifiable evidence.
- Site usage does not change legal rights, discharge debt or enforce rules.
