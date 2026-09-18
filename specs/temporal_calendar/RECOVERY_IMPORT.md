# Temporal Calendar Recovery Import — Custody Record

Source archive: StillPoint_Temporal_Core_GitHub_Recovery(1).zip

Archive SHA-256:
2cbd46a3efa46a827489f56cae51beb5ab537d2dff530b4cd1c48845114df612

## Audit result

The archive contained 28 files. The supplied 07_AUDIT/SHA256SUMS.txt validates
every listed file except its own self-referential checksum entry. That self
entry is not treated as custody proof for the checksum file itself. All
canonical documents, watch/UX lineage, implementation specs, donor files,
manuscript material, and audit documents otherwise matched the supplied hashes.

## Namespace correction

The recovered integration plan proposed stillpoint/temporal/. The live
repository already uses that namespace for the earned continuing-evidence and
temporal-authority layer. Calendar work therefore lives in
stillpoint/calendar_core/ rather than overwriting or diluting those guarantees.

## Version custody

The recovered September v3.0/v3.2 documents remain historical locked authority
of their versions. The current repository also contains a later v3.3 successor
candidate.

Both engines therefore exist explicitly:

- select_v32_nearest_legal — recovered v3.2 364/371 opening semantics.
- select_v33_nearest_spring_gate — v3.3 364-day ordinary year plus optional
  0/7-day interannual Reconciliation.

A caller must choose a version. Filename recency, code reuse, or a client
default cannot silently turn one version into the other.

## Recovered executable invariants

- apparent rise/set baseline uses Sun-center altitude about -0.8333 degrees;
- seven-day sequence remains continuous;
- 364 = 52 x 7 = 4 x 91;
- phase lengths are 30,30,31 repeated four times;
- six paired Enoch gates traverse twelve phases:
  4,5,6,6,5,4,3,2,1,1,2,3;
- 11/62 is a forecast/checksum, never an insertion schedule;
- Jubilee state is null unless an epoch is explicitly configured;
- protected-time functions return facts/flags and do not themselves execute
  suppression, sending, spending, publishing, or other consequential actions.

## Privacy

The exact Ground Zero street address and coordinates are not committed. Public
tests use a non-identifying Loveland-area reference point.
