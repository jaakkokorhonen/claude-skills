# Skill: link-check

Validates relative (internal) Markdown cross-references, using
[lychee](https://github.com/lycheeverse/lychee). Run it locally via the Claude
client skill, or directly from the command line, before committing a rename or
deletion — see the repo root `README.md`'s "No CI merge gate" note: there is
currently no GitHub Actions workflow running this automatically.

## Contents

- [What it checks](#what-it-checks)
- [Why external links are out of scope](#why-external-links-are-out-of-scope)
- [Running locally](#running-locally)
- [Extending scope to external links](#extending-scope-to-external-links)

---

## What it checks

Every relative link between Markdown files (e.g. `[Major Incident Management](./general-major-incident-management.md)`) is resolved against the filesystem. A rename or deletion that breaks a cross-reference fails the check with the offending file and link.

## Why external links are out of scope

The `--offline` flag (see [Running locally](#running-locally)) skips all `http(s)://` (and `mailto:`) links entirely — see `skills/link-check/lychee.toml`. This repo has many external references (cloud provider docs, status pages, changelogs); checking those over the network would make an otherwise deterministic, fast local check flaky on timeouts, rate limits, and transient outages unrelated to this repository's content. Internal links — the ones a rename or deletion in *this* repo can actually break — are the ones worth checking before every commit.

## Running locally

```bash
lychee --offline --no-progress --config skills/link-check/lychee.toml .
```

Install lychee via `cargo install lychee`, `brew install lychee`, or a release binary from the [lychee releases page](https://github.com/lycheeverse/lychee/releases) — no Python dependency, unlike `document-validator`.

## Extending scope to external links

If external-link rot becomes a real problem worth tracking, don't just drop `--offline` from routine local runs — that reintroduces the flakiness this skill was built to avoid. Instead, run a separate, occasional check without `--offline` (e.g. before a larger review pass) and treat its output as informational, reviewed manually or filed as an issue — not something that blocks a commit.
