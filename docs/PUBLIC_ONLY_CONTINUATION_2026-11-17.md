# Public-only StillPoint development continuation

**Date:** November 17, 2026  
**Status:** proposed engineering operating path; no release or promotion authority conferred

## Purpose

Keep StillPoint development moving using **already-public source** and the GitHub-hosted standard runners available to public repositories, without requiring an additional private-repository Actions budget. Maintain the distinction between an executable public Core and other independent codebases and evidence archives.

## Authoritative public working base

- **Active Core:** `FortCollinsBarber-netizen/StillPoint-Core-Canonical`, default branch `main`.
- **Public runtime lane:** `RobertEmmanuelLaDay/StillPoint-` is a separately versioned finite-warrant runtime; it does not replace or author the current Calendar Core.
- **Historical export:** `RobertEmmanuelLaDay/StillPoint-Core` is a source/provenance archive and is **not** an active development or promotion target.
- Keep the current selected Core temporal rules, finite publication, policy boundaries, authorial provenance, and historical evidence separate. A passing workflow is engineering evidence, not new jurisdiction or civil enactment.

## Evidence that the public path runs

On November 17, 2026, the existing Core CI and Apple Watch Common Calendar CI both completed successfully on GitHub-hosted runners:

- [Core CI run #44088514711](https://github.com/FortCollinsBarber-netizen/StillPoint-Core-Canonical/actions/runs/44088514711) — completed, success; includes actual Python tests and package checks.
- [Apple Watch Common Calendar CI run #44088514978](https://github.com/FortCollinsBarber-netizen/StillPoint-Core-Canonical/actions/runs/44088514978) — completed, success.

These runs qualify the **tested public Core heads and their exact workflows**, not the unexecuted branches of any other repository.

## Operating rules for public-only continuation

1. **Do not change the visibility** of any other repository as part of this path. Preserve independent repositories and their source history.
2. **Do not import or publish nonpublic source, documents, build artifacts, CI logs, git history, credentials, tokens, personal records, or private repository contents** into a public branch, job or artifact. This includes network checkout using an access token. A public runner cannot safely qualify a private product merely by copying it to public storage.
3. **Use only source that is already public, or separately cleared for publication.** Explicit source/provenance review is required before a new component crosses that boundary; don't infer permission from a dependency or from access to its repository.
4. **Continue in focused public branches and pull requests.** Run the existing `ubuntu-latest` Core CI and relevant Apple Watch checks on every proposed change. Preserve passing run IDs and exact tested commit IDs.
5. **Do not trade verification for a green badge.** If a test requires unavailable private inputs, report that test as *not run* instead of substituting mocks and claiming it passed.
6. **Keep no-charge infrastructure the default.** No payment-method changes, private-runner retries, premium runners, or paid external AI calls are authorized by this plan. Public Actions being free does not mean all API calls or third-party services are free.
7. **Protect public release rights.** Visibility does not itself grant reuse rights; choose and review explicit licensing before representing the software as freely redistributable.
8. **Do not change selected authority** or publish new Calendar years through a development-plan PR. Calendar successor decisions need their own author-directed review and tests.

## Practical next engineering milestones

1. **Public-Core-only baseline** — confirm the active Core `main` remains green on its existing full CI and on the first public continuation PR; make no code-path changes purely to mask a runner failure elsewhere.
2. **Public-safe development** — move new, self-contained Core/calendar/client improvements through a narrowly scoped PR and executable hosted checks.
3. **Public runtime interoperability** — where needed, derive a narrow interface using existing *public* Core and *public* runtime source only, with independently executed contract tests. Do not import any unpublished system's code or historical archives.
4. **Deferred private qualification** — preserve its open corrections and pin identities. Only mark another system qualified when its own exact source and required tests have actually executed in a permitted environment.
5. **Publish free access deliberately** — keep source availability, access to outcomes, and administrative control separate, with an explicit reviewed license and security posture.

## Decision record

The public-only path is the current **development infrastructure choice**, not a decision to abandon preserved work, not a repo visibility change, not a claim that account billing explains every runner rejection, and not a final cross-system release. This proposal adds no private files and makes no change to the active runtime.
