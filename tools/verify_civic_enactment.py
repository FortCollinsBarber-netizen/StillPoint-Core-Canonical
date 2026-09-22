#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import date, datetime
from pathlib import Path

from stillpoint.calendar_core.astronomy import (
    AstronomyEvidence,
    MappingAstronomyProvider,
)
from stillpoint.calendar_core.models import GeoPoint
from stillpoint.calendar_core.publication import (
    publication_digest,
    validate_publication_document,
)
from stillpoint.calendar_core.reference_rule import (
    select_v33_nearest_spring_gate_from_provider,
)
from stillpoint.calendar_core.sunset import apparent_sunset_utc

ROOT = Path(__file__).resolve().parents[1]
CIVIC = ROOT / "temporal" / "civic-enactment-v1"
APPLE = ROOT / "clients" / "apple-watch" / "CivicClock" / "Resources"
FREEZE = "9c35130daecd6d74063d2ef9140e2b3348e049ad"
FREEZE_TREE = "c0f0e4a2071b9b65e8b9a5ac38b436b2da032c02"
LAW_SHA = "84827168daf527240180fb739ccfcc5d3fff028d5394e705aa213195f6bda830"
PROOF_SHA = "89264787f5bd0aa326d198305a3e71056b0952e4055bcd1bccd6d7d4651e3176"


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def assert_equal(actual, expected, label: str) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: {actual!r} != {expected!r}")


def main() -> None:
    enactment = load(CIVIC / "enactment.json")
    ground = load(CIVIC / "ground_zero_pilot_location.json")
    eph_path = CIVIC / "ephemeris_usno_2026_2027.json"
    ephemeris = load(eph_path)
    pub_path = CIVIC / "published_calendar.json"
    publication = load(pub_path)
    policy = load(CIVIC / "apple_publication_policy.json")

    subprocess.run(
        ["git", "merge-base", "--is-ancestor", FREEZE, "HEAD"],
        check=True,
        cwd=ROOT,
    )

    freeze = enactment["calendarCoreFreeze"]
    assert_equal(freeze["commit"], FREEZE, "freeze commit")
    assert_equal(freeze["tree"], FREEZE_TREE, "freeze tree")
    assert_equal(
        sha(ROOT / "stillpoint/contracts/calendar_core_spec.json"),
        LAW_SHA,
        "calendar law digest",
    )
    assert_equal(
        sha(ROOT / "stillpoint/contracts/calendar_projection_vectors.json"),
        PROOF_SHA,
        "projection proof digest",
    )

    ref = enactment["acts"]["referencePoint"]
    coords = ground["coordinates"]
    for key in ("latitude", "longitude"):
        assert_equal(coords[key], ref[key], f"Ground Zero {key}")

    material = (
        f"GROUND_ZERO\n{ref['latitude']:.8f}\n"
        f"{ref['longitude']:.8f}\n"
        f"{ref['coordinateCustodyNonce']}"
    ).encode("utf-8")
    coordinate_digest = hashlib.sha256(material).hexdigest()
    assert_equal(
        coordinate_digest,
        ref["coordinateCustodyDigest"],
        "coordinate custody digest",
    )
    assert_equal(
        coordinate_digest,
        publication["referencePoint"]["coordinateCustodyDigest"],
        "publication coordinate digest",
    )

    ephemeris_sha = sha(eph_path)
    assert_equal(
        ephemeris_sha,
        enactment["acts"]["ephemerisAuthority"]["custodySHA256"],
        "ephemeris custody digest",
    )
    assert_equal(
        ephemeris_sha,
        publication["ephemerisEvidence"]["sha256"],
        "publication ephemeris digest",
    )

    assert_equal(
        publication_digest(publication),
        publication["publicationDigest"],
        "publication digest",
    )

    envelope = validate_publication_document(
        publication,
        authorized_authority_ids={
            enactment["acts"]["publicationAuthority"]["id"]
        },
        require_authority_status="pilot",
        expected_reference_rule_version="v3.3-candidate",
        expected_reference_station_id="GROUND_ZERO",
        expected_ephemeris_id="USNO_AA_SEASONS_API",
        expected_ephemeris_sha256=ephemeris_sha,
        at_opening=date.fromisoformat(
            enactment["acts"]["firstOpening"]["civilDate"]
        ),
    )

    first = enactment["acts"]["firstOpening"]
    point = GeoPoint(
        ref["latitude"],
        ref["longitude"],
        "GROUND_ZERO",
    )
    opening_utc = apparent_sunset_utc(
        date.fromisoformat(first["civilDate"]),
        point,
    ).isoformat().replace("+00:00", "Z")
    assert_equal(opening_utc, first["openingUTC"], "first opening UTC")

    evidence_row = next(
        row for row in ephemeris["marchEquinoxes"]
        if row["year"] == 2027
    )
    evidence = AstronomyEvidence(
        event="march_equinox",
        year=2027,
        instant_utc=datetime.fromisoformat(
            evidence_row["instantUTC"].replace("Z", "+00:00")
        ),
        source_id=ephemeris["source"],
        evidence_sha256=ephemeris_sha,
    )
    provider = MappingAstronomyProvider(
        provider_id=ephemeris["source"],
        evidence_by_year={2027: evidence},
    )
    decision = select_v33_nearest_spring_gate_from_provider(
        current_opening=date.fromisoformat(first["civilDate"]),
        evidence_year=2027,
        provider=provider,
        reference_point=point,
    )
    row = publication["years"][0]
    assert_equal(
        decision.reconciliation_days,
        row["reconciliationDaysAfterCompletion"],
        "Reconciliation decision",
    )
    assert_equal(
        decision.reason_code,
        row["reconciliationReasonCode"],
        "Reconciliation reason",
    )
    assert abs(
        decision.immediate_error_seconds - row["immediateErrorSeconds"]
    ) < 1e-6
    assert abs(
        decision.delayed_error_seconds - row["delayedErrorSeconds"]
    ) < 1e-6

    resource_sha = sha(pub_path)
    expected_policy = {
        "authorityID": envelope.authority_id,
        "authorityStatus": envelope.authority_status,
        "referencePointID": envelope.reference_station_id,
        "referenceRuleVersion": envelope.reference_rule_version,
        "ephemerisSource": envelope.ephemeris_id,
        "ephemerisSHA256": envelope.ephemeris_sha256,
        "publicationDigest": envelope.publication_digest,
        "resourceSHA256": resource_sha,
    }
    for key, value in expected_policy.items():
        assert_equal(policy[key], value, f"Apple policy {key}")

    if (APPLE / "published_calendar.json").read_bytes() != pub_path.read_bytes():
        raise AssertionError("Apple publication bytes differ from civic source")
    if (
        (APPLE / "apple_publication_policy.json").read_bytes()
        != (CIVIC / "apple_publication_policy.json").read_bytes()
    ):
        raise AssertionError("Apple policy bytes differ from civic source")

    print("CIVIC_ENACTMENT_AUDIT_PASS")
    print(json.dumps({
        "freezeCommit": FREEZE,
        "freezeTree": FREEZE_TREE,
        "coordinateCustodyDigest": coordinate_digest,
        "ephemerisSHA256": ephemeris_sha,
        "publicationDigest": envelope.publication_digest,
        "resourceSHA256": resource_sha,
        "authority": envelope.authority_id,
        "referencePoint": envelope.reference_station_id,
        "firstOpening": first["civilDate"],
        "reconciliationAfter2026": decision.reconciliation_days,
        "expiresAtOpening": envelope.publication_range.expires_at_opening.isoformat(),
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
