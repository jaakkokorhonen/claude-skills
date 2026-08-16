---
name: versioning
description: Apply consistent version numbering and approval tracking to operational and compliance documentation in continuous-ops, satisfying ISO 27001 Clause 7.5.3 and GDPR Art. 5(2), 30, 35.
---

# Skill: versioning

## Purpose

Apply consistent version numbering to operational documentation in the `continuous-ops` repository, satisfying:
- **ISO 27001:2022 Clause 7.5.3** — controlled documented information with version history and approval records
- **GDPR Art. 5(2), 30, 35** — accountability, RoPA accuracy, and DPIA audit trail

Call this skill whenever you create, edit, review, or publish any `.md` file that contains a `version` field in its frontmatter.

---

## Core Rule: Version Reflects Document Maturity, Not Git History

The `version` field tracks **content maturity and approval state** — not the number of commits or PRs. Git provides the full edit history; `version` answers only: *"has this document been formally reviewed and approved?"*

This distinction satisfies ISO 27001:2022 Clause 7.5.3, which requires version identification as evidence of document control — not as a proxy for edit count.

---

## Version Number Schema

| Stage | Version | Meaning |
|---|---|---|
| New, never reviewed | `0.1` | Initial development — anything may change (SemVer rule 4: major version zero is unstable) |
| Revised pre-publication draft | `0.2`, `0.3` … | Incremented only when a draft goes through a formal review cycle and is returned for revision |
| First formal publication | `1.0` | Document is `published` for the first time after completing the review cycle |
| Minor post-publication update | `1.1`, `1.2` … | A review cycle with content changes but no structural overhaul |
| Major structural revision | `2.0` | A review cycle that rewrites or restructures the document significantly |

**Compliance note:** `1.0` signals to an ISO auditor or DPA that this document has been formally approved. Never set `version: "1.0"` on a draft — it misrepresents the document's approval state.

---

## Rules by Lifecycle State

### `status: draft`
- Version is always `0.1` on creation.
- **Do not increment version** when making edits to a draft. Git history records all changes; `version` does not track edits.
- Exception: if a draft undergoes a formal review cycle and is **rejected and returned**, increment to `0.2` when the next revision cycle begins.

### `status: review`
- Version stays at its current `0.x` value.
- Do not increment when moving a document from `draft` to `review`.

### `status: published` (first publication)
- **Set `version: "1.0"`** at the moment of first publication.
- Update `last_reviewed` and `next_review` — this is the first real review date.
- For compliance documents (`type: policy`, e.g. DPIA.md, ISMS-related): also set `approved_by` (see Compliance Fields below).
- **Trigger a GitHub Release tag** for compliance documents (see Release Tagging below).

### `status: published` (subsequent review cycles)
- **Minor update** (corrected steps, updated references, small additions): increment patch → `1.1`, `1.2`, etc.
- **Major revision** (structure overhauled, scope changed, process fundamentally rewritten): increment major → `2.0`.
- Always add a `changelog` entry and update `last_reviewed`, `next_review`, and `approved_by`.
- **Trigger a GitHub Release tag** for compliance documents.

### `status: outdated`, `deprecated`, `archived`
- Do not increment version. The version reflects the last reviewed and approved state.
- ISO 27001 Clause 7.5.3 requires that superseded versions are either archived with restricted access or removed from active circulation. Ensure deprecated/archived documents are not reachable from the README index.

---

## Compliance Fields (ISO 27001 + GDPR)

For documents with `type: policy` (this includes compliance documents like DPIA.md — `dpia` is not a valid `type`, see CONTRIBUTING.md's type enum), or any document referenced in an SoA or RoPA, the following additional frontmatter fields are **required at first publication**:

```yaml
approved_by: dpo          # Role that approved the document (e.g. dpo, service-manager, ciso)
approved_date: 2026-08-15 # ISO 8601 date of formal approval
```

**Why:** ISO 27001:2022 Clause 7.5.3 requires evidence that documented information has been approved for adequacy. GDPR Art. 35(7)(d) requires that the DPO was consulted and their advice recorded. The `approved_by` + `approved_date` pair satisfies both requirements as an inline audit trail.

For non-compliance documents (`type: sop`, `type: guide`, `type: template`), these fields are optional but recommended for SOC and major incident SOPs.

Add the field definitions to the frontmatter schema in CONTRIBUTING.md when first used.

---

## `last_reviewed` and `next_review` Rules

| Lifecycle state | `last_reviewed` | `next_review` |
|---|---|---|
| `draft` (new) | Set to creation date (ISO 8601) | Creation date + `review_interval_days` |
| First `published` | Set to publication/approval date | Approval date + `review_interval_days` |
| Re-reviewed `published` | Update to review date | Review date + `review_interval_days` |
| `outdated`, `deprecated`, `archived` | Do not change | Do not change |

> `last_reviewed` on a draft means "created on this date" — not "formally reviewed". This is a known simplification accepted for operational continuity. The distinction becomes meaningful and must be accurate from first publication onward.

---

## Changelog Rules

- Add a `changelog` entry for **every PR** that changes file content, regardless of whether the version number changes.
- Format (most recent first):
  ```yaml
  changelog:
    - date: 2026-08-15
      change: Added approved_by field; promoted to published
    - date: 2026-08-01
      change: Initial draft
  ```
- Do **not** add a changelog entry for automated frontmatter-only date rollover with no content change.
- For compliance documents: the changelog entry at `status: published` must include the approver role, e.g. *"Approved by DPO; promoted to published v1.0"*.

---

## Frontmatter Helper Tool

To save token consumption in the Claude client, use the deterministic [`frontmatter_helper.py`](./frontmatter_helper.py) script instead of having the language model manually update and compute dates or versions.

```bash
# Example: Promote a draft policy to published (bumps version, sets last_reviewed/next_review, and appends a changelog entry)
python3 skills/versioning/frontmatter_helper.py \
  ISO-27001-Audit.md \
  --status published \
  --version-bump publish \
  --approved-by dpo \
  --change "Approved by DPO; promoted to published v1.0"
```

---

## Release Tagging (ISO 27001 Audit Trail)

ISO 27001:2022 Clause 7.5.3 requires that an auditor can retrieve the state of documented information at any point in time. Git commits satisfy this technically, but a named GitHub Release provides a human-readable, auditor-accessible snapshot.

### When to create a GitHub Release

| Event | Required? | Tag format |
|---|---|---|
| Any compliance document (`type: policy` — e.g. DPIA.md, ISMS SoA, risk register) promoted to `published` | **Yes** | `compliance/YYYY-MM-DD` |
| Batch of SOPs promoted to `published` in a single review cycle | Recommended | `ops/vYYYY.MM` |
| No compliance documents changed | No | — |

### Release tag format

```
compliance/2026-08-15
ops/v2026.08
```

### Automated Tagging Tool

The `versioning` skill includes a python automation script [`release_tagger.py`](./release_tagger.py). Run this script inside the repository workspace to automatically scan the latest git commit and create local git tags for any compliance documents or SOPs promoted to `published`:

```bash
python3 skills/versioning/release_tagger.py
```

### Release notes template

```markdown
## Compliance snapshot — 2026-08-15

### Documents promoted to published
- `gdpr-dpia-continuous-ops.md` v1.0 — approved by DPO 2026-08-15
- `iso-27001-audit-readiness.md` v1.0 — approved by service-manager 2026-08-15

### Documents updated
- `soc-security-incident-post-mortem.md` v1.2 — minor corrections

### Auditor reference
This release represents the ISMS documentation state as of 2026-08-15.
Commit: <SHA>
```

### What NOT to tag
- Draft-only PRs (no `published` documents changed)
- Frontmatter-only date rollovers
- Automated lint fixes

---

## Decision Flowchart

```
Are you creating a new file?
  → Set version: "0.1", status: draft
  → Set last_reviewed: today, next_review: today + review_interval_days
  → STOP

Are you editing an existing file?
  → Is status: draft or review?
      → Do NOT change version
      → Add changelog entry
      → STOP
  → Is status: published?
      → Is this a formal review cycle?
          → No  → Do NOT change version; add changelog entry → STOP
          → Yes → Minor changes?  → version 1.x → 1.x+1
                  Major rewrite?  → version x.0 → x+1.0
                  Update last_reviewed, next_review
                  Is document type: policy (e.g. a compliance document like a DPIA)?
                    → Update approved_by, approved_date
                    → Create GitHub Release tag compliance/YYYY-MM-DD
                  → STOP

Are you publishing a document for the first time (draft/review → published)?
  → Set version: "1.0"
  → Set last_reviewed and next_review to today / today + interval
  → Set approved_by and approved_date (if compliance document)
  → Create GitHub Release tag (if compliance document)
  → STOP
```

---

## Anti-Patterns

- ❌ `version: "1.0"` on a new document that has never been reviewed
- ❌ Incrementing version from `1.0` to `1.1` while document is still `draft`
- ❌ Incrementing version on every PR or commit
- ❌ Publishing a DPIA to `status: published` without `approved_by` and `approved_date`
- ❌ Omitting a GitHub Release when a compliance document is first published
- ❌ Leaving a deprecated document in the README index (ISO 27001 Clause 7.5.3 requires obsolete documents be identified and controlled)
