"""Unit tests for the two imperative-shell, file-on-disk wrappers:
validate_file() and fix_markdown_style().

The actual validation rules are covered in test_validate_text.py against
in-memory strings; this file only checks that validate_file() reads the
path off disk and delegates correctly, and that fix_markdown_style() writes
its corrections back to disk correctly (--fix's underlying function).
"""
from pathlib import Path

from document_validator import validate_file, fix_markdown_style

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


def test_validate_file_reads_and_delegates(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text(VALID_FM, encoding="utf-8")
    assert validate_file(p) == []


def test_validate_file_surfaces_errors_from_disk(tmp_path: Path):
    p = tmp_path / "test.md"
    p.write_text(VALID_FM.replace("status: draft", "status: unknown"), encoding="utf-8")
    errors = validate_file(p)
    assert any("Invalid status" in e for e in errors)


def test_fix_markdown_style_corrects_file(tmp_path: Path):
    p = tmp_path / "test.md"
    # Bad formatting: trailing whitespace, missing blank lines around headings, no eof newline
    bad_content = (
        VALID_FM.replace("Body\n", "Body \n# Heading 1\nSome text")
    )
    p.write_text(bad_content, encoding="utf-8")
    
    assert fix_markdown_style(p) is True
    
    fixed_content = p.read_text(encoding="utf-8")
    # Verify fixes: trailing space gone, blank lines added, ends with single newline
    assert "Body\n" in fixed_content
    assert "\n\n# Heading 1\n\nSome text\n" in fixed_content
    assert fixed_content.endswith("\n")
    assert not fixed_content.endswith("\n\n")
