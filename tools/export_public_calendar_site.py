#!/usr/bin/env python3
"""Export a browser-ready, read-only calendar entirely from public Canonical Core.

This is a consumer-data builder, not another calendar implementation. Every
single displayed Common date, sacred overlay, protected-time description,
observance and Jubilee coordinate comes from calendar_day_payload().
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from stillpoint.calendar_core.runtime_surface import (
    calendar_day_payload,
    load_enacted_publication,
)
from stillpoint.public_assistant import (
    WEEK_READ,
    answer_request,
    verify_answer_receipt,
)

ROOT = Path(__file__).resolve().parents[1]
SITE_SOURCE = ROOT / "site" / "stillpoint-calendar" / "index.html"
FIRST_YEAR = 2026
LAST_YEAR = 2075
DAY_COUNT = 364
SCHEMA = "stillpoint.public-calendar-static.v1"
ASSISTANT_SCHEMA = "stillpoint.public-assistant-static-weeks.v1"
OBSERVANCE_INDEX_SCHEMA = "stillpoint.public-observance-index.v1"
MAX_PUBLIC_OBSERVANCE_ROWS = 10_000


def _write_json(path: Path, value: object) -> str:
    payload = json.dumps(
        value, ensure_ascii=False, separators=(",", ":"), sort_keys=True,
    ).encode("utf-8")
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def _consumer_day(payload: dict) -> dict:
    """Only project already-calculated, published Core values; no new date law."""
    common = payload["common_date"]
    return {
        "civil_date": payload["civil_window"]["opens"],
        "calendar_address": payload["calendar_address"],
        "common_date": {
            key: common[key] for key in (
                "year", "month", "day", "ordinal",
                "week", "day_in_week", "weekday",
            )
        },
        "sacred_date": payload["sacred_date"],
        "observances": [
            {
                "id": item["id"],
                "name": item["name"],
                "jurisdiction": item["jurisdiction"],
                "rule": item["rule"],
                "note": item["note"],
                "source_refs": item["source_refs"],
                "source_coordinate": item["source_coordinate"],
                "profile_id": item["profile_id"],
                "projection_status": item["projection_status"],
            }
            for item in payload["observances"]
        ],
        "is_sabbath_date": payload["protected_time"]["is_sabbath_date"],
        "jubilee": {
            "year": payload["jubilee"]["year"],
            "cycle": payload["jubilee"]["cycle"],
            "is_jubilee_year": payload["jubilee"]["is_jubilee_year"],
            "is_sabbatical_threshold": payload["jubilee"]["is_sabbatical_threshold"],
        },
    }


def export_site(output: Path, years: list[int] | None = None) -> dict:
    source = load_enacted_publication()
    rows = source["years"]
    if (
        len(rows) != LAST_YEAR - FIRST_YEAR + 1
        or [int(row["year"]) for row in rows]
        != list(range(FIRST_YEAR, LAST_YEAR + 1))
    ):
        raise ValueError("cannot export from an unexpected publication boundary")
    if not SITE_SOURCE.is_file():
        raise FileNotFoundError("static site source is missing")

    selected = (
        list(range(FIRST_YEAR, LAST_YEAR + 1)) if years is None else list(years)
    )
    if len(selected) != len(set(selected)) or selected != sorted(selected):
        raise ValueError("export years must be distinct and in increasing order")
    if any(year < FIRST_YEAR or year > LAST_YEAR for year in selected):
        raise ValueError("cannot export an unpublished year")
    if not selected:
        raise ValueError("at least one published year is required")

    output.mkdir(parents=True, exist_ok=True)
    data_dir = output / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    assistant_dir = data_dir / "assistant"
    assistant_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(SITE_SOURCE, output / "index.html")

    digest = source["publicationDigest"]
    entries = []
    observance_rows: list[dict] = []
    for year in selected:
        days = []
        for ordinal in range(1, DAY_COUNT + 1):
            full = calendar_day_payload(year, ordinal)
            if (
                full["common_date"]["year"] != year
                or full["common_date"]["ordinal"] != ordinal
                or full["publication"]["digest"] != digest
                or full["map"]["last_year"] != LAST_YEAR
            ):
                raise ValueError("Core returned inconsistent publication data")
            record = _consumer_day(full)
            days.append(record)
            for observance in record["observances"]:
                # Only index annotations projected from the public Core.
                # An occurrence is addressed by its exact published Common day;
                # no recurrence or Gregorian date is calculated by the indexer.
                observance_rows.append({
                    "calendar_address": record["calendar_address"],
                    "civil_date": record["civil_date"],
                    "common_date": record["common_date"],
                    **observance,
                })
        # A year shard is small enough to load on demand in a phone browser.
        name = "Y_" + str(year) + ".json"
        sha = _write_json(
            data_dir / name,
            {
                "schema": SCHEMA + ".year",
                "year": year,
                "publication_digest": digest,
                "days": days,
            },
        )
        # These are complete answers produced by the installed public Core
        # assistant, NOT answers synthesized in JavaScript. Each answer is
        # independently reproduced by the canonical Python verifier at build
        # time; the static browser only presents these precomputed receipts.
        receipts = []
        for week in range(1, 53):
            request = f"Show Common Calendar week {week} of {year}."
            receipt = answer_request(
                request, allowed_capabilities=frozenset({WEEK_READ}),
            )
            if (
                receipt.get("status") != "completed"
                or receipt["result"]["week"] != week
                or receipt["result"]["year"] != year
                or receipt["result"]["publication"]["digest"] != digest
                or len(receipt["result"]["days"]) != 7
                or not verify_answer_receipt(receipt)["verified"]
            ):
                raise ValueError("public assistant answer did not reproduce")
            receipts.append(receipt)
        assistant_name = "Y_" + str(year) + ".json"
        assistant_sha = _write_json(
            assistant_dir / assistant_name,
            {
                "schema": ASSISTANT_SCHEMA,
                "year": year,
                "publication_digest": digest,
                "receipts": receipts,
            },
        )
        entries.append({
            "year": year,
            "assistant_path": "data/assistant/" + assistant_name,
            "assistant_sha256": assistant_sha,
            "assistant_week_count": len(receipts),
            "first_civil_date": days[0]["civil_date"],
            "last_civil_date": days[-1]["civil_date"],
            "count": len(days),
            "path": "data/" + name,
            "sha256": sha,
        })

    if len(observance_rows) > MAX_PUBLIC_OBSERVANCE_ROWS:
        raise ValueError("public observance search index exceeds the finite bound")
    observance_jurisdictions = sorted({
        item["jurisdiction"] for item in observance_rows
    })
    observance_index_name = "observances.json"
    observance_index_hash = _write_json(
        data_dir / observance_index_name,
        {
            "schema": OBSERVANCE_INDEX_SCHEMA,
            "publication_digest": digest,
            "first_common_year": selected[0],
            "last_common_year": selected[-1],
            "year_count": len(selected),
            "occurrence_count": len(observance_rows),
            "jurisdictions": observance_jurisdictions,
            "rows": observance_rows,
        },
    )

    manifest = {
        "schema": SCHEMA,
        "source": "published Canonical Core calendar_day_payload",
        "assistant_source": "stillpoint.public_assistant.answer_request",
        "assistant_verification": "verify_answer_receipt at build time; no in-browser Python",
        "assistant_schema": ASSISTANT_SCHEMA,
        "observance_index_schema": OBSERVANCE_INDEX_SCHEMA,
        "observance_index_path": "data/" + observance_index_name,
        "observance_index_sha256": observance_index_hash,
        "observance_index_count": len(observance_rows),
        "observance_index_jurisdictions": observance_jurisdictions,
        "authority": "read-only-consumer-projection",
        "publication_digest": digest,
        "first_common_year": FIRST_YEAR,
        "last_common_year": LAST_YEAR,
        "year_days": DAY_COUNT,
        "complete_publication": len(selected) == 50,
        "no_2076_publication": True,
        "years": entries,
    }
    _write_json(data_dir / "index.json", manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build an offline-ready browser calendar from existing public Core"
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--years", nargs="+", type=int,
        help="Optional subset for tests only; default builds all 50 published years",
    )
    args = parser.parse_args(argv)
    result = export_site(args.output, years=args.years)
    print(json.dumps({
        "output": str(args.output),
        "years": len(result["years"]),
        "days": len(result["years"]) * DAY_COUNT,
        "complete_publication": result["complete_publication"],
        "publication_digest": result["publication_digest"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
