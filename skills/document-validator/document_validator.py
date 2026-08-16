#!/usr/bin/env python3
"""
document_validator.py
Validates YAML frontmatter AND Markdown style in all Markdown files. Run
locally (see README.md's "No CI merge gate" note — there is no automated
enforcement of this beyond the local pre-commit hook). Pass --fix to
auto-correct the Markdown style issues listed below (not the frontmatter
schema issues — those need a human/agent decision).

Frontmatter rules, driven by CONTRIBUTING.md's schema:
  - Every .md file must have frontmatter, EXCEPT the FRONTMATTER_EXEMPT set
    below (README.md, CONTRIBUTING.md, etc.) — those still get the Markdown
    style checks below, just not this section.
  - Required fields for ALL types: title, tags, category, type, status,
    version, classification, review_owner, review_interval_days,
    last_reviewed, next_review, changelog
  - Additional required field when type == sop: sop_id
  - Additional required fields when status == deprecated:
      deprecated_date, deprecated_reason, superseded_by
  - Additional required fields (approved_by, approved_date) when
    status == published and type == policy
  - Allowed status values: draft, review, published, outdated, deprecated, archived
  - Allowed type values: sop, guide, appendix, template, policy
  - Allowed classification values: public, internal, confidential, restricted,
    customer confidential
  - Every tag in `tags` must appear in TAG_TAXONOMY below
  - next_review must be last_reviewed + review_interval_days (+-3 day tolerance)
  - changelog must be a non-empty list; each entry needs date + change keys
  - Marp files (marp: true) must have marp key inside the SINGLE frontmatter block

Markdown style rules (validate_markdown_style()), checked on every .md file
including FRONTMATTER_EXEMPT ones, skipped for Marp files where noted:
  - File must end with exactly one newline
  - No line may have trailing whitespace (fenced code blocks excepted)
  - Headings must be preceded and followed by a blank line (skipped for Marp)
  - Heading levels may only increment by 1 at a time, e.g. H2 -> H3, not H2 -> H4
    (skipped for Marp)
"""

# Requires Python 3.9+: builtin generics are subscripted directly at
# runtime below (tuple[...], list[...]), which is PEP 585 and needs no
# `from __future__ import annotations`. Nothing in this repo states a lower
# floor, so this isn't tested against older interpreters. If a real need
# to support <3.9 shows up, add the future import instead of rewriting
# these hints.
import argparse
import sys
import re
import yaml
from pathlib import Path
from datetime import date, timedelta
from typing import Optional

__version__ = "1.1.0"

REQUIRED_ALL = [
    "title", "tags", "category", "type", "status", "version",
    "review_owner", "review_interval_days", "last_reviewed",
    "next_review", "changelog", "classification",
]
REQUIRED_SOP = ["sop_id"]
REQUIRED_DEPRECATED = ["deprecated_date", "deprecated_reason", "superseded_by"]

ALLOWED_STATUSES = {"draft", "review", "published", "outdated", "deprecated", "archived"}
ALLOWED_TYPES    = {"sop", "guide", "appendix", "template", "policy"}
ALLOWED_CLASSIFICATIONS = {"public", "internal", "confidential", "restricted", "customer confidential"}

# Canonical tag taxonomy. Must always mirror the Tag Taxonomy section in the
# repo root CONTRIBUTING.md — two independent, hand-maintained copies of the
# same schema, same rule as ALLOWED_TYPES/ALLOWED_STATUSES above (see
# "Extending the schema" in this skill's README). Update both in one commit.
TAG_TAXONOMY = {
    "domain": {"appops", "dataops", "devops", "soc", "general"},
    "governance": {"policy", "audit", "isms", "dpia", "compliance", "privacy"},
    "process": {
        "incident-management", "major-incident", "escalation", "triage",
        "problem-management", "change-management", "release-management",
        "patching", "provisioning", "post-mortem",
    },
    "function": {
        "analyst-guide", "on-call", "shift-handover", "ticket-routing",
        "finops", "iam", "monitoring", "alerting", "detection",
        "threat-intelligence",
    },
    "cadence": {"monthly", "quarterly", "operational-calendar"},
    "audience": {"1st-line", "2nd-line", "3rd-line"},
}
ALLOWED_TAGS = set().union(*TAG_TAXONOMY.values())

# Exact relative paths (from repo root) exempt from the frontmatter SCHEMA
# requirement only — not from validation entirely. These files legitimately
# have no YAML frontmatter (they're meta-docs, not operational SOPs), but
# Markdown style rules (heading blank lines, trailing whitespace, EOF
# newline) still apply to them like any other .md file. Previously this set
# skipped these files from validate_file() altogether, which meant nothing
# ever checked README.md's own Markdown structure — a readme_helper.py bug
# went undetected because of exactly that gap (see its regression note).
FRONTMATTER_EXEMPT = {
    Path("README.md"),
    Path("CONTRIBUTING.md"),
    Path("CHANGELOG.md"),
    Path("AGENTS.md"),
    Path("CODE_OF_CONDUCT.md"),
    Path("SECURITY.md"),
}

DATE_TOLERANCE_DAYS = 3


def is_frontmatter_exempt(path: Path) -> bool:
    """Return True if *path* (relative to repo root) doesn't require frontmatter."""
    return path in FRONTMATTER_EXEMPT


def extract_frontmatter(text: str) -> tuple[Optional[dict], list[str]]:
    """Returns (parsed_dict_or_None, list_of_warnings)."""
    warnings = []
    if not text.startswith("---"):
        return None, ["No YAML frontmatter found (file must start with ---)"]
    end = text.find("---", 3)
    if end == -1:
        return None, ["Frontmatter opening --- found but no closing ---"]
    raw = text[3:end].strip()
    # Check for duplicate frontmatter blocks (Marp issue). A body that opens
    # with a Markdown horizontal rule ("---" on its own line, then prose) must
    # NOT trigger this: only flag it when a second "---"-delimited block
    # exists AND its content actually parses as a YAML mapping — that's the
    # real signature of a second frontmatter block, not a plain hr.
    rest = text[end + 3:]
    leading_rule = re.match(r"\s*---\s*\n", rest)
    if leading_rule:
        after_marker = rest[leading_rule.end():]
        second_close = after_marker.find("---")
        if second_close != -1:
            second_raw = after_marker[:second_close].strip()
            try:
                second_data = yaml.safe_load(second_raw)
            except yaml.YAMLError:
                second_data = None
            if isinstance(second_data, dict):
                warnings.append(
                    "DUPLICATE FRONTMATTER: A second --- block found after the first. "
                    "Marp keys (marp, theme, paginate) must be merged into the single "
                    "frontmatter block."
                )
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        return None, [f"YAML parse error: {exc}"]
    if not isinstance(data, dict):
        return None, ["Frontmatter did not parse as a YAML mapping"]
    return data, warnings


def validate_text(text: str, require_frontmatter: bool = True) -> list[str]:
    """Pure validation logic: Markdown text in, list of error strings out.

    No filesystem access here (functional core) — validate_file() below is
    the thin imperative-shell wrapper that does the actual file read. Tests
    can exercise validate_text() directly with in-memory strings instead of
    writing to tmp_path for every case.

    require_frontmatter=False is for FRONTMATTER_EXEMPT files: a plain body
    with no "---" block is expected and not an error, but Markdown style is
    still checked. A file that DOES start with "---" is still validated
    normally either way — exemption means "none required", not "ignored if
    present".
    """
    errors = []

    if not require_frontmatter and not text.startswith("---"):
        return validate_markdown_style(text, None)

    fm, warnings = extract_frontmatter(text)
    errors.extend(warnings)

    if fm is None:
        return errors

    # Required fields
    for field in REQUIRED_ALL:
        if field not in fm:
            errors.append(f"Missing required field: {field}")

    # type enum
    doc_type = fm.get("type")
    if doc_type and doc_type not in ALLOWED_TYPES:
        errors.append(f"Invalid type '{doc_type}'. Allowed: {sorted(ALLOWED_TYPES)}")

    # status enum
    status = fm.get("status")
    if status and status not in ALLOWED_STATUSES:
        errors.append(f"Invalid status '{status}'. Allowed: {sorted(ALLOWED_STATUSES)}")

    # classification enum
    classification = fm.get("classification")
    if classification and classification not in ALLOWED_CLASSIFICATIONS:
        errors.append(
            f"Invalid classification '{classification}'. Allowed: {sorted(ALLOWED_CLASSIFICATIONS)}"
        )

    # sop_id required when type == sop
    if doc_type == "sop":
        for field in REQUIRED_SOP:
            if field not in fm:
                errors.append(f"Missing required field for type=sop: {field}")

    # deprecated fields
    if status == "deprecated":
        for field in REQUIRED_DEPRECATED:
            if field not in fm:
                errors.append(f"Missing required field for status=deprecated: {field}")

    # iso_controls must be a list if present
    iso_controls = fm.get("iso_controls")
    if iso_controls is not None and not isinstance(iso_controls, list):
        errors.append("iso_controls must be a YAML list")

    # date math: next_review == last_reviewed + review_interval_days
    lr       = fm.get("last_reviewed")
    nr       = fm.get("next_review")
    interval = fm.get("review_interval_days")
    if lr and nr and interval:
        try:
            lr_date  = lr if isinstance(lr, date) else date.fromisoformat(str(lr))
            nr_date  = nr if isinstance(nr, date) else date.fromisoformat(str(nr))
            expected = lr_date + timedelta(days=int(interval))
            delta    = abs((nr_date - expected).days)
            if delta > DATE_TOLERANCE_DAYS:
                errors.append(
                    f"next_review ({nr_date}) is {delta} days off from "
                    f"last_reviewed ({lr_date}) + {interval} days = {expected}. "
                    f"Tolerance is +-{DATE_TOLERANCE_DAYS} days."
                )
        except (ValueError, TypeError) as exc:
            errors.append(f"Date parsing error: {exc}")

    # changelog: non-empty list, each entry has date + change
    changelog = fm.get("changelog")
    if changelog is not None:
        if not isinstance(changelog, list) or len(changelog) == 0:
            errors.append("changelog must be a non-empty list")
        else:
            for i, entry in enumerate(changelog):
                if not isinstance(entry, dict):
                    errors.append(f"changelog[{i}] is not a mapping")
                    continue
                for key in ("date", "change"):
                    if key not in entry:
                        errors.append(f"changelog[{i}] missing key: {key}")

    # tags must be a list, and every tag must be in the canonical taxonomy
    tags = fm.get("tags")
    if tags is not None:
        if not isinstance(tags, list):
            errors.append("tags must be a YAML list")
        else:
            unknown = sorted({t for t in tags if t not in ALLOWED_TAGS})
            for tag in unknown:
                errors.append(
                    f"Unknown tag '{tag}'. Allowed tags: {sorted(ALLOWED_TAGS)}. "
                    "Add new tags to the Tag Taxonomy in CONTRIBUTING.md and "
                    "mirror them in TAG_TAXONOMY in document_validator.py first."
                )

    # approved_by and approved_date validation
    approved_by = fm.get("approved_by")
    approved_date = fm.get("approved_date")

    def _is_blank(value: object) -> bool:
        """True for None or a whitespace-only string.

        `bool(x)` is NOT the same test: bool("") is False, so a field set to
        an empty string ("blank placeholder") used to be treated identically
        to the field being entirely absent everywhere below — including the
        "must be provided together" check, which compared bool(approved_by)
        to bool(approved_date) and saw two "false"s as a match. That let
        `approved_by: ""` / `approved_date: ""` ship silently, with zero
        validation errors, on three real documents (DPIA.md,
        ISO-27001-Audit.md, information-security-policy.md) before this was
        caught by manually walking the versioning skill's own rules against
        them — the skill never says to pre-fill these fields with an empty
        placeholder before publication; either omit them or set real values.
        """
        return value is None or (isinstance(value, str) and value.strip() == "")

    # "dpia" is not a valid `type` (see ALLOWED_TYPES) — compliance documents
    # like DPIA.md use `type: policy` (confirmed: DPIA.md:9). Only check for
    # the reachable value; do not resurrect a dead "dpia" branch here.
    if status == "published" and doc_type == "policy":
        if _is_blank(approved_by):
            errors.append("Missing required field for published compliance document: approved_by")
        if _is_blank(approved_date):
            errors.append("Missing required field for published compliance document: approved_date")

    if approved_by is not None and _is_blank(approved_by):
        errors.append("approved_by must be a non-empty string")

    if approved_date is not None:
        if _is_blank(approved_date):
            errors.append("approved_date must not be empty")
        else:
            try:
                if not isinstance(approved_date, date):
                    date.fromisoformat(str(approved_date))
            except (ValueError, TypeError):
                errors.append(f"Invalid approved_date '{approved_date}'. Expected ISO 8601 YYYY-MM-DD")

    if _is_blank(approved_by) != _is_blank(approved_date):
        errors.append("approved_by and approved_date must be provided together")

    # Markdown syntax / style validations
    errors.extend(validate_markdown_style(text, fm))

    return errors


def validate_markdown_style(text: str, fm: Optional[dict] = None) -> list[str]:
    errors = []
    fm = fm or {}
    is_marp = fm.get("marp") is True
    
    # 1. Check end of file ends with exactly one newline
    if not text.endswith("\n"):
        errors.append("File must end with a newline character")
    elif text.endswith("\n\n"):
        errors.append("File must end with exactly one newline character (no trailing empty lines)")

    lines = text.splitlines()

    # 2. Check each line for trailing whitespace
    in_code_block = False
    for i, line in enumerate(lines):
        if line.startswith("```"):
            in_code_block = not in_code_block
        if not in_code_block:
            if line.endswith(" ") or line.endswith("\t"):
                errors.append(f"Line {i+1} has trailing whitespace")

    # 3. Find headings and validate hierarchy and blank lines
    if not is_marp:
        headings = []
        in_code_block = False
        for i, line in enumerate(lines):
            if line.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue

            match = re.match(r"^(#{1,6})\s+(.*)$", line)
            if match:
                level = len(match.group(1))
                content = match.group(2)
                headings.append((i, level, content))

                # Headings must be surrounded by blank lines
                if i > 0:
                    prev_line = lines[i - 1]
                    if prev_line.strip() != "" and prev_line.strip() != "---":
                        errors.append(f"Heading at line {i+1} must be preceded by a blank line")
                if i < len(lines) - 1:
                    next_line = lines[i + 1]
                    if next_line.strip() != "" and next_line.strip() != "---":
                        errors.append(f"Heading at line {i+1} must be followed by a blank line")

        # Heading nesting hierarchy
        prev_level = 0
        for idx, (line_idx, level, content) in enumerate(headings):
            if prev_level > 0:
                if level > prev_level + 1:
                    errors.append(
                        f"Heading level skip at line {line_idx+1}: H{level} follows H{prev_level} "
                        "(headings must only increment by 1 level at a time)"
                    )
            prev_level = level

    return errors


def validate_file(path: Path, require_frontmatter: bool = True) -> list[str]:
    """Imperative shell: read *path* off disk, delegate to validate_text()."""
    return validate_text(path.read_text(encoding="utf-8"), require_frontmatter=require_frontmatter)


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate YAML frontmatter and Markdown style in Markdown files against the CONTRIBUTING.md schema."
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Root directory to scan for Markdown files (default: current directory).",
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Automatically fix Markdown style formatting issues (trailing spaces, heading blank lines, eof newlines).",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser.parse_args(argv)


def fix_markdown_style(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    original_text = text

    fm, _ = extract_frontmatter(text)
    is_marp = fm.get("marp") is True if fm else False

    lines = text.splitlines()

    # Strip trailing whitespace on all lines except inside code blocks
    in_code_block = False
    for i in range(len(lines)):
        if lines[i].startswith("```"):
            in_code_block = not in_code_block
        if not in_code_block:
            lines[i] = lines[i].rstrip()

    # Heading blank lines (if not marp)
    if not is_marp:
        fixed_lines = []
        in_code_block = False
        for i, line in enumerate(lines):
            if line.startswith("```"):
                in_code_block = not in_code_block
                fixed_lines.append(line)
                continue
            if in_code_block:
                fixed_lines.append(line)
                continue

            # If line is a heading
            if re.match(r"^(#{1,6})\s+(.*)$", line):
                if fixed_lines:
                    prev_line = fixed_lines[-1]
                    if prev_line.strip() != "" and prev_line.strip() != "---":
                        fixed_lines.append("")
                fixed_lines.append(line)
                if i < len(lines) - 1:
                    next_line = lines[i + 1]
                    if next_line.strip() != "" and next_line.strip() != "---":
                        fixed_lines.append("")
            else:
                fixed_lines.append(line)
        lines = fixed_lines

    # Reassemble and ensure exactly one trailing newline
    new_text = "\n".join(lines).rstrip("\n") + "\n"

    if new_text != original_text:
        path.write_text(new_text, encoding="utf-8")
        return True
    return False


def main() -> int:
    args         = parse_args()
    root         = Path(args.path)
    results_file = Path("document-validation-results.txt")
    # Stdout gets the short, as-given path (cheap to read for a human or an
    # agent driving this via CLI); the resolved absolute path only goes into
    # the results file, where it's useful for later audit but costs nothing
    # extra to a live reader.
    print(f"document-validator v{__version__} — scanning {args.path}")
    files = sorted(root.rglob("*.md"))

    if args.fix:
        print("Auto-fix enabled. Correcting Markdown style issues...")
        fixed_count = 0
        for f in files:
            rel = f.relative_to(root)
            # NOT is_frontmatter_exempt here: exempt files (README.md etc.)
            # still get their Markdown style auto-fixed, just not their
            # frontmatter schema. Only path/skills exclusions apply.
            if any(part.startswith(".") for part in rel.parts):
                continue
            if "skills" in rel.parts:
                continue
            if fix_markdown_style(f):
                print(f"Fixed: {f}")
                fixed_count += 1
        print(f"Auto-fix completed. Fixed {fixed_count} file(s).")

    total = 0
    failed = 0
    all_results = []
    report_lines = [f"document-validator v{__version__} — scanned {root.resolve()}\n"]

    for f in files:
        rel = f.relative_to(root)
        # Filter on rel.parts, not f.parts: f is rooted at whatever --path
        # happens to be (this runs locally, not in CI — see README.md's "No
        # CI merge gate" note). If that absolute path contains a "skills" or
        # dot-prefixed component above the repo root (e.g. a clone at
        # ~/work/.mirrors/skills-repo/), f.parts would silently exclude every
        # file and this would report a false "OK, 0/0 passed" instead of
        # failing loudly. rel.parts is always relative to root, so it only
        # reflects this repo's own structure.
        if any(part.startswith(".") for part in rel.parts):
            continue
        # skip the skills directory itself (meta-docs)
        if "skills" in rel.parts:
            continue
        total += 1
        errors = validate_file(f, require_frontmatter=not is_frontmatter_exempt(rel))
        if errors:
            failed += 1
            all_results.append((str(f), errors))

    if all_results:
        # ::error file=...:: is GitHub Actions annotation syntax — it drives
        # inline PR file comments ONLY when a workflow runs this and parses
        # stdout. There is currently no such workflow (see README.md's "No
        # CI merge gate" note), so today this is just structured stdout for
        # a human or agent reading the terminal. Kept as-is rather than
        # stripped: harmless now, and free to reactivate if CI returns.
        # The human-readable "FAIL file / - message" form of the same data
        # goes only into report_lines/results_file, not stdout — printing
        # both would just duplicate every error in the console output.
        print(f"::error::Document validation failed on {failed}/{total} file(s)")
        for filepath, errors in all_results:
            for err in errors:
                print(f"::error file={filepath}::{err}")

        report_lines.append(f"FAIL  Document validation failed on {failed}/{total} file(s)\n")
        for filepath, errors in all_results:
            report_lines.append(f"FAIL  {filepath}")
            for err in errors:
                report_lines.append(f"      - {err}")

        results_file.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
        return 1

    ok_line = f"OK  All {total} Markdown files passed document validation."
    print(ok_line)
    report_lines.append(ok_line)
    results_file.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
