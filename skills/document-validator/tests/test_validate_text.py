"""Unit tests for validate_text() — the pure validation core.

These exercise validate_text() directly with in-memory strings rather
than through validate_file()/tmp_path. See test_validate_file.py for the
(much smaller) coverage of the file-reading wrapper itself.
"""
import re

import pytest

from document_validator import validate_text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_FM = """\
---
title: Test SOP
tags:
  - general
category: ops
type: sop
sop_id: SOP-001
status: draft
classification: internal
version: "1.0"
review_owner: ops-team
review_interval_days: 90
last_reviewed: 2026-05-01
next_review: 2026-07-30
changelog:
  - date: 2026-05-01
    change: Initial version
---
Body
"""


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_valid_sop_passes():
    assert validate_text(VALID_FM) == []


# ---------------------------------------------------------------------------
# Required fields — parametrised so each field gets its own test case
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("field", [
    "title", "tags", "category", "type", "status", "classification",
    "version", "review_owner", "review_interval_days",
    "last_reviewed", "next_review", "changelog",
])
def test_missing_required_field(field):
    if field == "changelog":
        # changelog is a multi-line block; dropping only the "changelog:"
        # line and leaving its nested list items would corrupt the YAML
        # structure instead of simply omitting the field.
        content = VALID_FM.replace(
            "changelog:\n  - date: 2026-05-01\n    change: Initial version\n", ""
        )
    else:
        # Anchor on "field:" at line start, not just a string prefix, so a
        # field name that happens to prefix another key's line (or a value)
        # can't be dropped by accident.
        key_line = re.compile(rf"^{re.escape(field)}:")
        lines = [line for line in VALID_FM.splitlines() if not key_line.match(line)]
        content = "\n".join(lines)
    errors = validate_text(content)
    assert any(field in e for e in errors)


# ---------------------------------------------------------------------------
# Enum validation
# ---------------------------------------------------------------------------

def test_invalid_status():
    content = VALID_FM.replace("status: draft", "status: unknown")
    errors = validate_text(content)
    assert any("Invalid status" in e for e in errors)


def test_invalid_type():
    content = VALID_FM.replace("type: sop", "type: memo")
    # also remove sop_id so we don't get a confounding error
    content = content.replace("sop_id: SOP-001\n", "")
    errors = validate_text(content)
    assert any("Invalid type" in e for e in errors)


def test_invalid_classification():
    content = VALID_FM.replace("classification: internal", "classification: secret")
    errors = validate_text(content)
    assert any("Invalid classification" in e for e in errors)


def test_iso_controls_valid_list():
    content = VALID_FM.replace("status: draft", "status: draft\niso_controls:\n  - A.5.15\n  - A.8.2")
    assert validate_text(content) == []


def test_iso_controls_non_list_fails():
    content = VALID_FM.replace("status: draft", "status: draft\niso_controls: A.5.15")
    errors = validate_text(content)
    assert any("iso_controls must be a YAML list" in e for e in errors)


# ---------------------------------------------------------------------------
# SOP-specific fields
# ---------------------------------------------------------------------------

def test_sop_without_sop_id():
    content = VALID_FM.replace("sop_id: SOP-001\n", "")
    errors = validate_text(content)
    assert any("sop_id" in e for e in errors)


# ---------------------------------------------------------------------------
# Date math
# ---------------------------------------------------------------------------

def test_next_review_too_far():
    content = VALID_FM.replace("next_review: 2026-07-30", "next_review: 2027-01-01")
    errors = validate_text(content)
    assert any("days off" in e for e in errors)


def test_next_review_within_tolerance():
    """±3 days allowed: 2026-05-01 + 90 days = 2026-07-30; +2 days = 2026-08-01 is OK."""
    content = VALID_FM.replace("next_review: 2026-07-30", "next_review: 2026-08-01")
    assert validate_text(content) == []


def test_next_review_at_exact_tolerance_boundary():
    """Exactly +3 days (2026-08-02) is still within the +-3 day tolerance."""
    content = VALID_FM.replace("next_review: 2026-07-30", "next_review: 2026-08-02")
    assert validate_text(content) == []


def test_next_review_one_day_over_tolerance():
    """Exactly +4 days (2026-08-03) is one day past the +-3 day tolerance."""
    content = VALID_FM.replace("next_review: 2026-07-30", "next_review: 2026-08-03")
    errors = validate_text(content)
    assert any("days off" in e for e in errors)


# ---------------------------------------------------------------------------
# Changelog
# ---------------------------------------------------------------------------

def test_empty_changelog():
    content = VALID_FM.replace(
        "changelog:\n  - date: 2026-05-01\n    change: Initial version",
        "changelog: []"
    )
    errors = validate_text(content)
    assert any("non-empty" in e for e in errors)


def test_changelog_entry_missing_date():
    content = VALID_FM.replace(
        "  - date: 2026-05-01\n    change: Initial version",
        "  - change: Initial version"
    )
    errors = validate_text(content)
    assert any("missing key: date" in e for e in errors)


def test_changelog_entry_missing_change():
    content = VALID_FM.replace(
        "  - date: 2026-05-01\n    change: Initial version",
        "  - date: 2026-05-01"
    )
    errors = validate_text(content)
    assert any("missing key: change" in e for e in errors)


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

def test_tags_as_string_fails():
    content = VALID_FM.replace("tags:\n  - general", "tags: general")
    errors = validate_text(content)
    assert any("YAML list" in e for e in errors)


def test_unknown_tag_fails():
    content = VALID_FM.replace("tags:\n  - general", "tags:\n  - general\n  - made-up-tag")
    errors = validate_text(content)
    assert any("Unknown tag 'made-up-tag'" in e for e in errors)


def test_multiple_unknown_tags_each_reported():
    content = VALID_FM.replace(
        "tags:\n  - general", "tags:\n  - general\n  - bogus-one\n  - bogus-two"
    )
    errors = validate_text(content)
    assert any("Unknown tag 'bogus-one'" in e for e in errors)
    assert any("Unknown tag 'bogus-two'" in e for e in errors)


@pytest.mark.parametrize("tag", [
    "appops", "dataops", "devops", "soc", "general",
    "policy", "audit", "isms", "dpia", "compliance", "privacy",
    "incident-management", "major-incident", "escalation", "triage",
    "problem-management", "change-management", "release-management",
    "patching", "provisioning", "post-mortem",
    "analyst-guide", "on-call", "shift-handover", "ticket-routing",
    "finops", "iam", "monitoring", "alerting", "detection",
    "threat-intelligence", "monthly", "quarterly", "operational-calendar",
    "1st-line", "2nd-line", "3rd-line",
])
def test_every_taxonomy_tag_is_accepted(tag):
    content = VALID_FM.replace("tags:\n  - general", f"tags:\n  - {tag}")
    assert validate_text(content) == []


# ---------------------------------------------------------------------------
# Deprecated status — all three extra fields required
# ---------------------------------------------------------------------------

def test_deprecated_without_required_fields():
    content = VALID_FM.replace("status: draft", "status: deprecated")
    errors = validate_text(content)
    assert any("deprecated_date" in e for e in errors)
    assert any("deprecated_reason" in e for e in errors)
    assert any("superseded_by" in e for e in errors)


# ---------------------------------------------------------------------------
# Approval fields (approved_by, approved_date)
# ---------------------------------------------------------------------------

def test_published_policy_requires_approved_by_and_date():
    content = (
        VALID_FM.replace("type: sop\nsop_id: SOP-001", "type: policy")
        .replace("status: draft", "status: published")
    )
    errors = validate_text(content)
    assert any("approved_by" in e for e in errors)
    assert any("approved_date" in e for e in errors)


def test_valid_approved_by_and_date():
    content = (
        VALID_FM.replace("type: sop\nsop_id: SOP-001", "type: policy")
        .replace("status: draft", "status: published\napproved_by: dpo\napproved_date: 2026-08-15")
    )
    assert validate_text(content) == []


def test_invalid_approved_date():
    content = VALID_FM.replace(
        "status: draft",
        "status: draft\napproved_by: dpo\napproved_date: not-a-date"
    )
    errors = validate_text(content)
    assert any("Invalid approved_date" in e for e in errors)


def test_approval_fields_must_be_provided_together():
    content = VALID_FM.replace(
        "status: draft",
        "status: draft\napproved_by: dpo"
    )
    errors = validate_text(content)
    assert any("must be provided together" in e for e in errors)


def test_empty_string_approved_by_and_date_are_flagged():
    """Regression test: approved_by: "" / approved_date: "" (an empty-string
    placeholder, not an omitted field) previously produced ZERO errors —
    bool("") is False, so the presence checks treated a blank string
    identically to the field being absent. This shipped on DPIA.md,
    ISO-27001-Audit.md, and information-security-policy.md before being
    caught by manually testing the versioning skill's own rules against
    them."""
    content = VALID_FM.replace(
        "status: draft",
        'status: draft\napproved_by: ""\napproved_date: ""'
    )
    errors = validate_text(content)
    assert any("approved_by must be a non-empty string" in e for e in errors)
    assert any("approved_date must not be empty" in e for e in errors)
    # Neither field is meaningfully "provided" here, so the pairing check
    # correctly stays silent — the two errors above already flag the problem.
    assert not any("must be provided together" in e for e in errors)


def test_empty_string_approved_by_alone_still_triggers_pairing_error():
    """One blank, one real value: still a real mismatch, still flagged."""
    content = VALID_FM.replace(
        "status: draft",
        'status: draft\napproved_by: ""\napproved_date: 2026-08-15'
    )
    errors = validate_text(content)
    assert any("must be provided together" in e for e in errors)
    assert any("approved_by must be a non-empty string" in e for e in errors)


def test_published_policy_with_empty_string_placeholders_still_fails():
    content = (
        VALID_FM.replace("type: sop\nsop_id: SOP-001", "type: policy")
        .replace("status: draft", 'status: published\napproved_by: ""\napproved_date: ""')
    )
    errors = validate_text(content)
    assert any("Missing required field for published compliance document: approved_by" in e for e in errors)
    assert any("Missing required field for published compliance document: approved_date" in e for e in errors)


# ---------------------------------------------------------------------------
# Markdown style validations
# ---------------------------------------------------------------------------

def test_markdown_missing_eof_newline():
    content = VALID_FM.rstrip("\n")
    errors = validate_text(content)
    assert any("must end with a newline" in e for e in errors)


def test_markdown_multiple_eof_newlines():
    content = VALID_FM + "\n"
    errors = validate_text(content)
    assert any("trailing empty lines" in e for e in errors)


def test_markdown_trailing_whitespace():
    content = VALID_FM + "\nSome text with trailing space "
    errors = validate_text(content)
    assert any("has trailing whitespace" in e for e in errors)


def test_markdown_heading_spacing_missing_preceding_blank_line():
    content = VALID_FM + "\nSome text\n# Heading 1\n"
    errors = validate_text(content)
    assert any("must be preceded by a blank line" in e for e in errors)


def test_markdown_heading_spacing_missing_following_blank_line():
    content = VALID_FM + "\n# Heading 1\nSome text\n"
    errors = validate_text(content)
    assert any("must be followed by a blank line" in e for e in errors)


def test_markdown_heading_nesting_level_skip():
    content = VALID_FM + "\n# Heading 1\n\n### Heading 3\n"
    errors = validate_text(content)
    assert any("increment by 1 level" in e for e in errors)


def test_markdown_marp_headings_skipped():
    content = (
        VALID_FM.replace("status: draft", "status: draft\nmarp: true")
        + "\n# Heading 1\n### Heading 3\n"
    )
    assert validate_text(content) == []


def test_markdown_code_blocks_headings_and_spaces_skipped():
    content = (
        VALID_FM + "\n```\n# Heading inside code block\nline with space \n```\n"
    )
    assert validate_text(content) == []


# ---------------------------------------------------------------------------
# require_frontmatter=False (FRONTMATTER_EXEMPT files, e.g. README.md)
# ---------------------------------------------------------------------------

def test_exempt_file_without_frontmatter_only_checks_style():
    """No '---' block, require_frontmatter=False: not an error, and Markdown
    style is still checked — this is the exact bug class that shipped
    unnoticed in README.md because these files were skipped entirely."""
    content = "# Title\n\nSome text.\n"
    assert validate_text(content, require_frontmatter=False) == []


def test_exempt_file_style_violation_still_caught():
    content = "# Title\n### Skipped-level heading with no blank line before\n"
    errors = validate_text(content, require_frontmatter=False)
    assert any("must be preceded by a blank line" in e for e in errors)
    assert any("increment by 1 level" in e for e in errors)


def test_exempt_file_with_malformed_frontmatter_still_flagged():
    """Exemption means "none required", not "ignored if attempted" — a file
    that does start with '---' is still validated normally."""
    content = "---\nkey: [unclosed\n---\nBody\n"
    errors = validate_text(content, require_frontmatter=False)
    assert any("YAML parse error" in e for e in errors)


def test_default_require_frontmatter_true_unaffected():
    content = "# Title\n\nSome text.\n"
    errors = validate_text(content)
    assert any("must start with" in e for e in errors)



