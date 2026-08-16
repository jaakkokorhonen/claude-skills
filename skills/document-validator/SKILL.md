---
name: document-validator
description: Unified linter that validates both YAML frontmatter schemas and Markdown style best practices (heading nesting, blank line spacing, trailing whitespace, end-of-file newlines) across all repository documentation.
---

# Skill: document-validator

Unified validator for YAML frontmatter schemas and Markdown style best practices in this repository.
Run it locally via the Claude client skill, or directly from the command line, before committing —
see the repo root `README.md`'s "No CI merge gate" note: there is currently no GitHub Actions workflow running this.

## Contents

- [What it checks](#what-it-checks)
- [Tag taxonomy](#tag-taxonomy)
- [Files excluded from validation](#files-excluded-from-validation)
- [Running locally](#running-locally)
- [Known issue fixed: Marp double-frontmatter](#known-issue-fixed-marp-double-frontmatter)
- [Extending the schema](#extending-the-schema)

---

## What it checks

### 1. Frontmatter Validation
- Checks for required fields: `title`, `tags`, `category`, `type`, `status`, `version`, `review_owner`, `review_interval_days`, `last_reviewed`, `next_review`, `changelog`, `classification`.
- Checks values of `status`, `type`, `classification` against allowed enumerations.
- Enforces `sop_id` when `type: sop`.
- Enforces DPO approval fields (`approved_by`, `approved_date`) when `status: published` and `type: policy` (this includes compliance documents like `DPIA.md`, which uses `type: policy` — there is no separate filename-based check).
- Enforces date math checks: `next_review == last_reviewed + review_interval_days` (+-3 day tolerance).
- Enforces tag taxonomy matching.

### 2. Markdown Style Validation
- **Heading Nesting Hierarchy:** Heading levels must only increment by 1 level at a time (e.g. H2 followed by H3, H4; H3 cannot directly follow H1).
- **Blank Line Spacing:** Headings must be surrounded by blank lines. (Skipped for Marp slides).
- **End-of-File Newline:** Files must end with exactly one newline character (no trailing empty lines).
- **Trailing Whitespace:** No line may end with trailing space or tab characters. (Skipped inside fenced code blocks).

---

## Tag taxonomy

`TAG_TAXONOMY` / `ALLOWED_TAGS` in `document_validator.py` must always mirror the
**Tag Taxonomy** section in the repo root `CONTRIBUTING.md` — same rule as
`ALLOWED_TYPES`/`ALLOWED_STATUSES` (see [Extending the schema](#extending-the-schema)
below): two independent, hand-maintained copies of the same list, updated together
in one commit.

An unknown tag fails the check with an actionable error naming the offending tag,
the full allowed list, and where to add a new one.

To add a new tag:

1. Add it to the appropriate group in `CONTRIBUTING.md`'s Tag Taxonomy section.
2. Add it to the matching group in `TAG_TAXONOMY` in `document_validator.py`, in the same commit.

---

## Files excluded from validation

The following files are exempt from the frontmatter **schema** requirement only
(they are repository/tooling infrastructure, not operational SOPs/guides, so
they legitimately have no YAML frontmatter) — but Markdown **style** rules
(heading blank lines, trailing whitespace, EOF newline, heading nesting) still
apply to them like any other `.md` file, and `--fix` corrects them too:
- `README.md`
- `CONTRIBUTING.md`
- `CHANGELOG.md`
- `AGENTS.md`
- `CODE_OF_CONDUCT.md`
- `SECURITY.md`

All files in the `skills/` directory are fully skipped (frontmatter and style) — they're this skill's own meta-docs.

---

## Running locally

Requires Python 3.9+ and PyYAML.

```bash
# Install dependencies
pip install -r skills/document-validator/requirements.txt

# Run linter on the current directory
python skills/document-validator/document_validator.py

# Run on a specific path
python skills/document-validator/document_validator.py path/to/folder

# Run unit tests
pip install -r skills/document-validator/requirements-dev.txt
pytest skills/document-validator/tests/ -v
```

---

## Known issue fixed: Marp double-frontmatter

`service-overview-presentation.md` previously had two `---` blocks — the standardised
frontmatter block followed by the original Marp block (`marp: true`, `theme: default`,
`paginate: true`). Marp only reads the **first** `---` block, so `marp: true` was
silently ignored and the file no longer rendered as a slide deck.

**Fix:** merge both YAML blocks into one — put `marp`, `theme`, and `paginate` inside
the same frontmatter block as `title`, `tags`, etc. See `service-overview-presentation.md`
for the current source of truth.

The duplicate-block detector only flags a genuine second YAML mapping after the
first `---` close — a document body that simply opens with a Markdown horizontal
rule (`---` followed by prose) is not flagged.

---

## Extending the schema

`ALLOWED_TYPES`, `ALLOWED_STATUSES`, and `TAG_TAXONOMY` in this script must always
mirror the `type`, `status`, and Tag Taxonomy sections documented in the repo root
`CONTRIBUTING.md`. They are independent, hand-maintained copies of the same schema —
if you change one without the other, the validator will start rejecting (or silently
accepting) values that disagree with the documented contract. Update both in the
same commit.
