# Public Calendar browser — first assistant interface

**Stage:** reviewed public-source candidate, not proof of deployment. This integrates the bounded public Python assistant introduced in PR #100 with the existing public Calendar browser from PR #98. The static site does not run the Python assistant on every visitor request.

## User experience

Select an ordinary Gregorian date in the existing browser. The page identifies its Common year and week using the published Core-generated year shard. In the assistant panel choose **Show verified week answer** to load the prepared Python assistant answer for that exact Common year/week, including the seven-day result and its downloadable JSON receipt.

The receipt has the same schema as the installed command:

```sh
stillpoint ask "Show Common Calendar week 46 of 2026." > receipt.json
stillpoint verify-answer receipt.json
```

The UI makes only published week reads available. It does not accept an arbitrary free-form request and does not claim to be a live Python service, a natural-language AI model, or an autonomous agent.

## Data integrity and provenance

During every public export, `tools/export_public_calendar_site.py` invokes `answer_request` with the explicit single capability `calendar.week.read` and invokes `verify_answer_receipt` independently on the complete result. For each published year the exporter writes an assistant data shard containing 52 actual, independently reproduced week receipts. There are exactly **50 years × 52 weeks = 2,600** week receipts for the finite enacted **2026–2075** publication.

The public manifest lists the assistant shard paths, SHA-256 hashes, expected schema and record counts. The browser uses **Web Crypto SHA-256** over downloaded shard bytes before displaying a receipt and performs additional bounded schema/authority checks. Without HTTPS or a trusted localhost browser context, assistant receipts cannot be displayed because the integrity primitive is unavailable.

The SHA-256 check detects divergence from the delivered manifest but **does not authenticate the website operator or prove historical consent**. A successful downloaded receipt may be reproduced against the matching installed public source using `stillpoint verify-answer`. Neither file hashing nor a matching receipt grants action authority. The verification also depends on the exact installed source and calendar publication; use matching source if verifying older receipts.

The browser only displays precomputed answers, which are fixed at export time. It cannot answer every free-form calendar question from the command line. The installed `stillpoint ask` and `stillpoint verify-answer` remain the canonical bounded live local workflow.

## Build locally

```sh
python -m pip install .
python -m unittest discover -s tests/calendar_core -p 'test_public_calendar_site_export.py' -v
python tools/export_public_calendar_site.py --output /tmp/stillpoint-public-browser
cd /tmp/stillpoint-public-browser
python -m http.server 8000
```

Visit `http://localhost:8000/` from a modern browser. The exporter builds the 18,200 existing published day records **and** 2,600 assistant week receipts. The two site workflows verify complete finite publication before any artifact is eligible for deployment.

## Release boundaries

- Source and public CI may pass **without** GitHub Pages being enabled. A live site, keyboard/mobile behavior and actual downloaded receipt verification against a deployed version require separate evidence.
- No provider keys, new repository, company database, private RobertOS/StillPointOS source, private pins, payment service or long-lived authorization tokens are used.
- No unpublished Common 2076 calendar or assistant shard is exported.
- The pre-Christian calendar sources, post-Christian protected-time application, sacred anchor and Jubilee model are unchanged; the UI consumes only the already selected Core calculation.
- Checkpoint 004 private integration, historical source custody, personal authorization and production operations remain separate qualification gates.
