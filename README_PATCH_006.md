# Patch 006 — Canonical RC Closure

Patch 006 is a release/custody closure patch. It adds no runtime capability.

It:
- makes `FortCollinsBarber-netizen/StillPoint-Core-Canonical` the self-described canonical repository;
- preserves the original verified Patch 005 source-tree and canonical tags;
- reconciles package, runtime, checkpoint, release-note, and release-manifest version metadata at `0.2.0rc1`;
- preserves the prior `0.1.0-rc1` release notes as historical custody material;
- adds deterministic release-metadata/provenance auditing;
- keeps schema 9, migrations 001–009, existing authority boundaries, frozen evaluator hashes, and disabled production adapters unchanged.

The next capability milestone is Patch 007: the first bounded production-adapter path.
