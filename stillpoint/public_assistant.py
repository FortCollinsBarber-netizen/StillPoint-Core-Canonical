"""Bounded public request -> permission -> Calendar Core -> evidence workflow.

This is a deterministic read-only assistant, not a general language model or a
company execution adapter. The caller must supply the public read permission.
Receipts reproduce public data; they are neither signatures nor action warrants.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any

from .authority.deterministic import assess_bundle
from .calendar_core.civil_lookup import civil_date_lookup_payload
from .calendar_core.governor import RHYTHM_GOVERNOR, RhythmAuthority, RhythmRequest
from .calendar_core.runtime_surface import calendar_day_payload, load_enacted_publication
from .calendar_core.week_view import calendar_week_payload

ANSWER_SCHEMA = "stillpoint.public-assistant-answer.v1"
DAY_READ = "calendar.day.read"
WEEK_READ = "calendar.week.read"
OBSERVANCES_READ = "calendar.observances.read"
PUBLIC_READ_CAPABILITIES = frozenset({DAY_READ, WEEK_READ, OBSERVANCES_READ})
MAX_REQUEST_CHARACTERS = 512
MAX_RECEIPT_BYTES = 256_000
_ROOT = Path(__file__).resolve().parent
_SOURCES = (
    "public_assistant.py", "authority/deterministic.py", "authority/clauses.py",
    "authority/schema.py", "calendar_core/civil_lookup.py",
    "calendar_core/runtime_surface.py", "calendar_core/week_view.py",
    "calendar_core/observances.py",
    "calendar_core/governor.py", "calendar_core/publication.py",
    "contracts/calendar_publication_2026_2075.json",
)
_EXAMPLES = (
    "What is the Common Calendar date for 2026-11-17?",
    "Show the Common Calendar week for 2026-11-17.",
    "Show Common Calendar week 12 of 2027.",
    "Show Common Calendar day 364 of 2075.",
    "Explain Common Calendar observances for 2026-11-17.",
    "Explain Common Calendar observances on Common day 1 of 2027.",
)


def _digest(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _seal(value: dict[str, Any]) -> dict[str, Any]:
    return {**value, "receipt_sha256": _digest(value)}


def interpret_request(request: str) -> dict[str, Any] | None:
    """Recognize only an entire supported request, never an actionable prefix."""
    if type(request) is not str or not 0 < len(request) <= MAX_REQUEST_CHARACTERS:
        return None
    text = request.strip()
    common = r"(?:the )?common(?: calendar)? "
    show = r"show(?: me)? "
    iso = r"([0-9]{4}-[0-9]{2}-[0-9]{2})"
    explain = r"(?:explain|list)(?: the)? common(?: calendar)? observances (?:for|on) "
    patterns = (
        (explain + r"(?:gregorian )?" + iso,
         OBSERVANCES_READ, ("civil_date",)),
        (explain + r"common day ([0-9]{1,3}) (?:of|in) ([0-9]{4})",
         OBSERVANCES_READ, ("ordinal", "year")),
        (r"(?:what is |" + show + r")" + common + r"date for (?:gregorian )?" + iso,
         DAY_READ, ("civil_date",)),
        (show + common + r"week (?:for|containing) (?:gregorian )?" + iso,
         WEEK_READ, ("civil_date",)),
        (show + common + r"week ([0-9]{1,2}) (?:of|in) ([0-9]{4})",
         WEEK_READ, ("week", "year")),
        (show + common + r"day ([0-9]{1,3}) (?:of|in) ([0-9]{4})",
         DAY_READ, ("ordinal", "year")),
    )
    for pattern, capability, keys in patterns:
        match = re.fullmatch(pattern + r"[?.]?", text, flags=re.I | re.ASCII)
        if match:
            args = {key: value if key == "civil_date" else int(value)
                    for key, value in zip(keys, match.groups())}
            return {"capability": capability, "arguments": args}
    return None


def _project(plan: dict[str, Any]) -> dict[str, Any]:
    """Dispatch through a fixed allowlist; request text cannot name a function."""
    RHYTHM_GOVERNOR.require(RhythmRequest(RhythmAuthority.READ, "public-assistant"))
    args = plan["arguments"]
    if "civil_date" in args:
        day = civil_date_lookup_payload(args["civil_date"])["calendar_day"]
        if plan["capability"] in {DAY_READ, OBSERVANCES_READ}:
            return day
        return calendar_week_payload(day["common_date"]["year"], day["common_date"]["week"])
    if plan["capability"] in {DAY_READ, OBSERVANCES_READ}:
        return calendar_day_payload(args["year"], args["ordinal"])
    return calendar_week_payload(args["year"], args["week"])


def _check_projection(result: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    publication = load_enacted_publication()
    rows = publication["years"]
    expected_schema = ("stillpoint.calendar-week.v1" if plan["capability"] == WEEK_READ
                       else "stillpoint.calendar-day.v2")
    if (result.get("schema") != expected_schema
            or result.get("authority") != "read-only-calendar-law"
            or result["publication"]["digest"] != publication["publicationDigest"]
            or result["map"]["first_year"] != rows[0]["year"]
            or result["map"]["last_year"] != rows[-1]["year"]
            or result["map"]["year_count"] != len(rows)):
        raise ValueError("Core result does not match the current finite publication")
    return publication


def _label(day: dict[str, Any]) -> str:
    return f"{day['year']:04d}-{day['month']:02d}-{day['day']:02d}"


def _answer(plan: dict[str, Any], result: dict[str, Any]) -> str:
    civil = plan["arguments"].get("civil_date")
    if plan["capability"] == OBSERVANCES_READ:
        day = result["common_date"]
        events = result["observances"]
        label = f"Common {_label(day)} ({day['weekday']})"
        if not events:
            return (f"{label} has no named observances in the published StillPoint "
                    "Common Calendar. This does not negate separate Sabbath, "
                    "protected-time, or external-calendar overlays.")
        details = []
        for event in events:
            parts = [
                f"{event['name']} (jurisdiction: {event['jurisdiction']}; "
                f"Core rule: {event['rule']}; projection: {event['projection_status']})",
            ]
            if event["source_refs"]:
                parts.append("source references: " + "; ".join(event["source_refs"]))
            if event["note"]:
                parts.append("Core note: " + event["note"])
            details.append("; ".join(parts))
        return (f"{label} records {len(events)} named StillPoint observance(s): "
                + " | ".join(details)
                + ". These are published Core annotations, not automatic civil "
                  "enactments or prescriptions for other communities.")
    if plan["capability"] == DAY_READ:
        day = result["common_date"]
        prefix = f"Gregorian {civil} is " if civil else ""
        return (f"{prefix}Common {_label(day)} ({day['weekday']}), "
                f"Common week {day['week']}.")
    first, last = result["days"][0]["common_date"], result["days"][-1]["common_date"]
    prefix = f"Gregorian {civil} falls in " if civil else ""
    return (f"{prefix}Common year {result['year']}, week {result['week']}: "
            f"Common {_label(first)} through {_label(last)} (7 days).")


def answer_request(request: str, *,
                   allowed_capabilities: frozenset[str] = frozenset()) -> dict[str, Any]:
    """Execute at most one supported public-read request under caller permission.

    Permission is checked before any calendar lookup. It is scoped to this call;
    it creates no durable grant, company approval, warrant, or external action.
    """
    if type(request) is not str:
        raise ValueError("request must be text")
    if (type(allowed_capabilities) is not frozenset
            or not allowed_capabilities <= PUBLIC_READ_CAPABILITIES):
        raise ValueError("allowed_capabilities must be a frozenset of public calendar reads")
    # Bound input before the existing consequential-intent assessment is called.
    plan = interpret_request(request)
    restricted = (assess_bundle(request).restricted_intents
                  if 0 < len(request) <= MAX_REQUEST_CHARACTERS else [])
    base: dict[str, Any] = {
        "schema": ANSWER_SCHEMA,
        "request": request[:MAX_REQUEST_CHARACTERS],
        "interpretation": plan,
        "authorization": {"allowed": False, "scope": "this-request-only",
                          "execution_warrant": False},
        "result": None,
        "evidence": None,
    }
    if len(request) > MAX_REQUEST_CHARACTERS:
        return _seal({**base, "status": "unsupported", "request_truncated": True,
                      "answer": "Requests are limited to 512 characters; no prefix was executed."})
    if restricted:
        return _seal({**base, "status": "denied",
                      "answer": "This assistant can only read the public calendar; this request includes a consequential action."})
    if plan is None:
        return _seal({**base, "status": "unsupported",
                      "answer": "Use one complete supported calendar request with an explicit date or year.",
                      "examples": list(_EXAMPLES)})
    capability = plan["capability"]
    if capability not in allowed_capabilities:
        return _seal({**base, "status": "denied",
                      "answer": f"The caller has not permitted {capability} for this request."})
    base["authorization"] = {
        "allowed": True, "scope": "this-request-only", "capability": capability,
        "basis": "invoking-caller-public-read-permission", "execution_warrant": False,
    }
    try:
        result = _project(plan)
        publication = _check_projection(result, plan)
        evidence = {
            "kind": "reproducible-public-read-not-a-signature-or-warrant",
            "request_sha256": _digest(request),
            "result_sha256": _digest(result),
            "publication_digest": publication["publicationDigest"],
            "sources": [{"path": "stillpoint/" + name,
                         "sha256": hashlib.sha256((_ROOT / name).read_bytes()).hexdigest()}
                        for name in _SOURCES],
        }
    except (ValueError, OSError, KeyError, TypeError) as exc:
        return _seal({**base, "status": "unavailable", "answer": str(exc)})
    return _seal({**base, "status": "completed", "answer": _answer(plan, result),
                  "result": result, "evidence": evidence})


def verify_answer_receipt(receipt: Any) -> dict[str, Any]:
    """Reproduce a completed public read from current code/data, without state.

    A recomputed self-hash alone is insufficient: the complete answer, Core
    result, source hashes and scope must match a fresh bounded reproduction.
    This verifies reproducibility, not the original caller's identity or consent.
    """
    answer = {"schema": "stillpoint.public-assistant-verification.v1", "verified": False}
    if (type(receipt) is not dict or receipt.get("schema") != ANSWER_SCHEMA
            or receipt.get("status") != "completed"
            or type(receipt.get("request")) is not str):
        return {**answer, "reason": "a completed public assistant receipt is required"}
    plan = interpret_request(receipt["request"])
    if plan is None:
        return {**answer, "reason": "request is outside the supported public-read scope"}
    expected = answer_request(receipt["request"],
                              allowed_capabilities=frozenset({plan["capability"]}))
    try:
        matches = _digest(receipt) == _digest(expected)
    except (TypeError, ValueError, RecursionError):
        matches = False
    if expected["status"] != "completed" or not matches:
        return {**answer, "reason": "receipt does not reproduce against the current public source and data"}
    return {**answer, "verified": True, "receipt_sha256": expected["receipt_sha256"],
            "reason": "answer, result, source bytes and bounded scope reproduce; no action authority is granted"}


def read_answer_receipt(path: Path) -> Any:
    if not path.is_file():
        raise ValueError("receipt must be a regular JSON file")
    with path.open("rb") as stream:
        raw = stream.read(MAX_RECEIPT_BYTES + 1)
    if len(raw) > MAX_RECEIPT_BYTES:
        raise ValueError("receipt exceeds the public assistant size limit")
    try:
        return json.loads(raw)
    except (ValueError, RecursionError) as exc:
        raise ValueError("receipt must contain valid bounded JSON") from exc
