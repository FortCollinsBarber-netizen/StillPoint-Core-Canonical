# Public assistant: request through verified result

The first bounded assistant interaction runs an existing public Calendar Core
capability from an explicit user request and returns a reproducible receipt.
It works locally from the installed package without a provider account.

```bash
python -m pip install .
stillpoint ask "Show the Common Calendar week for 2026-11-17."
```

The answer is Common year 2026, week 46: Common November 12 through November 18.
The JSON also contains the seven actual Core-projected days, the interpreted
request, permission decision, publication digest, relevant source-file hashes,
result hash and receipt hash.

An [actual installed-workflow answer](examples/public_assistant_week_answer.json)
is retained with this change. With the matching installed source, reproduce it:

```bash
stillpoint verify-answer docs/examples/public_assistant_week_answer.json
```

## Supported requests

- `What is the Common Calendar date for 2026-11-17?`
- `Show the Common Calendar week for 2026-11-17.`
- `Show Common Calendar week 12 of 2027.`
- `Show Common Calendar day 364 of 2075.`

`Common Calendar` may be shortened to `Common`; case and a final period or
question mark do not matter. Dates must be explicit Gregorian `YYYY-MM-DD`
translation inputs, or explicitly labeled Common year/week/day coordinates.
Here “day” in a Common year means its ordinal, 1–364. Relative requests such as
“today” are unsupported. The recognizer matches the entire request; appended
instructions never execute a valid prefix.

## Permission and execution

1. Recognize one supported request and assess consequential intent through the
   existing Core authority assessor.
2. Check caller permission for exactly `calendar.day.read` or
   `calendar.week.read` before querying calendar data.
3. Ask the existing RhythmGovernor for READ and invoke existing day, civil-date
   lookup or week projection functions. Calendar law is not reimplemented.
4. Confirm the Core schema, read-only authority and current finite publication.
5. Return the answer, real result and its evidence receipt.

The explicit `stillpoint ask` invocation grants only the supported public reads
for that invocation. Python callers use `answer_request(text,
allowed_capabilities=frozenset({...}))`; the default permission is empty.
The permission is not retained. No company approval or warrant is created.
Compound, unsupported, unpermitted, invalid and unpublished requests cannot
report completion. The `ask` CLI exits 0 on completion and 2 otherwise.

The flow does not construct CompanyRuntime, instantiate a provider, open a
company database, request a credential, consult private sources, create a task,
send a message, publish, pay, delete, change canon, or extend the finite map.
The ordinary company submission and consequential-action routes stay separate.

## Verify an answer

The caller may explicitly save stdout and verify it in a fresh process:

```bash
stillpoint ask "Show the Common Calendar week for 2026-11-17." > answer.json
stillpoint verify-answer answer.json
```

`verify-answer` performs only bounded public reads. It reproduces the complete
request interpretation, answer, Core result, permission scope and observed
source-byte hashes against the current installed code/data. Editing a result
and recalculating its hashes is insufficient to pass. Changed source bytes or
publication data invalidate reproduction under that installation. Files larger
than 256,000 bytes are rejected. Verification exits 0 on reproduction and 2 on
rejection, with a structured JSON verdict.

A receipt is not a signature, proof of caller identity, proof of historical
consent, or an execution warrant. Source hashes identify the listed files, not
an attestation of every dependency or the host. Verification never authorizes a
consequential action or revives an old approval. Source custody, physical solar
event calculations, private retrieval/memory, open-ended conversation and
production operation remain separate capabilities.

## Qualification

New tests exercise real read results, missing/wrong permission, compound and
oversized requests, finite boundaries, tampered results with recomputed hashes,
source evidence, and receipt rejection. Installed-process tests use Python
isolated mode from an empty working directory with a provider selected but no
provider credentials. They verify request -> receipt -> independent verification
and that no company state appears. They are discovered by existing Core CI;
no new workflow or repository is needed.

This source milestone does not change GitHub Pages settings, private dependency
pins, private cross-system qualification, calendar authority or release status.
