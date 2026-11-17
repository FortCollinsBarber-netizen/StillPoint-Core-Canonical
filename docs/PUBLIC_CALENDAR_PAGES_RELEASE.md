# Public Calendar — GitHub Pages release boundary

**Status:** Prepared deployment workflow; do not describe the public calendar as a live hosted website until a successful deployment URL has been verified in a browser.

## Current evidence (November 17, 2026)

- Public Canonical Core `main` includes the calendar browser via PR #98, commit `1d04d1152957cebdd73465f5e5a9d7c7997186c4`.
- The existing public Calendar browser build tests, full Core CI, and public continuity checks passed on that commit.
- Live verification of the expected URL, `https://fortcollinsbarber-netizen.github.io/StillPoint-Core-Canonical/`, returned GitHub's **404 Site not found** page on November 17.
- The browser export is a 50-year finite public projection, **2026–2075**, containing 18,200 read-only Core-generated days.
- That is an already-built *site source and local static output*, **not** a deployed GitHub Pages site.

## Prepared path

The independent `.github/workflows/public-calendar-pages.yml` workflow:

1. Checks the existing repository's Pages status using only the ephemeral `GITHUB_TOKEN`. It makes **no repository-setting changes**.
2. Proceeds only if the repository reports GitHub Pages enabled with the **GitHub Actions** publishing source. Otherwise it reports the missing configuration, skips deployment, and succeeds safely.
3. After readiness is established, reruns the public Core browser export tests, builds all 18,200 published days, and verifies no unpublished Common year 2076 shard exists.
4. Uploads **only** the generated static site through a pinned official Pages artifact action, then deploys the exact artifact through a pinned official Pages deployment action from `main`.
5. Never checks out or copies private RobertOS, StillPointOS, the writing corpus, secrets, archived commits, or unqualified release candidates.

This workflow reuses the existing public repository and public Ubuntu runners. It does not create another repository or require paid AI services.

## One-time GitHub configuration that the current connector cannot perform

A repository administrator must enable the Pages site and select the **GitHub Actions** publishing source:

`https://github.com/FortCollinsBarber-netizen/StillPoint-Core-Canonical/settings/pages`

GitHub documents the setting under **Settings → Pages → Build and deployment → Source: GitHub Actions**. Once enabled, dispatch the existing **StillPoint Calendar Pages publication** workflow (or push a scoped public site update to `main`). The guarded workflow will generate, verify and deploy.

Do not supply a personal access token merely to bypass this setting. The official `configure-pages` action explicitly requires a non-`GITHUB_TOKEN` credential to auto-enable Pages; this project is not creating or exposing one.

## Release acceptance

Publish status requires all of:

- Protected public Core tests and the full browser exporter pass on the exact released commit.
- The Pages deployment job reports a URL.
- A fresh remote browser request to the deployed URL returns HTTP 200 and the actual StillPoint calendar page (not the GitHub source view).
- Its `/data/index.json` returns the expected 50-year, 18,200-day publication index.
- Mobile/keyboard basic interactions are exercised against the live site.

The existing private integration and Apple Watch qualification remain independent; successful Pages publication does not qualify them.
