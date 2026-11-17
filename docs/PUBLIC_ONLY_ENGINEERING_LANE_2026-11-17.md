# Public-only engineering lane — Checkpoint 004

**Decision date:** November 17, 2026. **Project author:** Robert Emmanuel LaDay.
**Status:** engineering and qualification boundary; not a civil enactment, private-code publication, or production release.

## Continue on public Canonical Core

This repository already hosts the active, author-selected StillPoint Calendar Core and
Apple Watch shared resources. A new public-only GitHub Actions gate,
`.github/workflows/public-core-qualification.yml`, can execute with standard
GitHub-hosted Ubuntu runners without consuming the private-repository compute
allowance. It checks out **only this already-public repository**, installs its
own source package, and verifies the public runtime contract.

Local/CI command:

```sh
python -m pip install .
python -m unittest discover -s tests/public_core -p 'test_*.py' -v
```

The public tests guard the v2 read-only calendar interface, 364-day / 52-week
geometry, March 25 sacred source-year coordinate distinct from civil January 1,
the dated 2027 overlap-49 Jubilee selection, alternative rollover models as
comparison-only, distinct Friday civil dusk–Sunday civil dawn versus sacred
sunset, and the finite 2026–2075 publication. Calculating a 2076 Jubilee
proclamation does **not** publish a 2076 calendar or enact any civil/legal
release. The working rules are subject to later documented authorized
supersession and testing.

## Protected private sources stay unchanged

The existing private RobertOS, StillPointOS, StillPoint, and writing-corpus
repositories remain protected as repository histories, source custody and
unpublished research. Their failed GitHub-hosted runner admission is an
infrastructure limitation, not a reason to expose their historical commits,
secrets, source intake, letters or Actions logs. Do not convert them to public
or copy their contents into public CI to obtain a passing badge.

The currently proposed RobertOS and StillPointOS successor PRs and their
independent offline evidence remain **unqualified in private GitHub Actions**.
This public gate does **not** execute or qualify their source; a public Core
PASS cannot be re-labeled as a three-repository PASS.

## Next public engineering increments

Extend the already-public Core's documented law, read-only interfaces,
package-level tests, public Watch resources and public-safe demos through
ordinary review and green public CI. For a future reusable consumer library,
write **new**, clean-room public code based exclusively on already-published
Core contracts and an affirmative publication decision; never transplant
private modules or full Git history as a shortcut.

This preserves a zero-additional-hosted-compute-cost public testing lane,
without requiring payment, relaxing authority boundaries, or changing
repository visibility. Making code public is not itself a grant of an open
source license; any future redistribution license is a separate author decision.
