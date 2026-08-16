#!/usr/bin/env python3
"""
frontmatter_helper.py
Deterministic assistant script to update frontmatter properties (statuses,
approvals, dates, and version increments) without using language model tokens.
"""
import argparse
import sys
import yaml
from pathlib import Path
from datetime import datetime, timedelta

def parse_args() -> argparse.Namespace:
    """
    Parse command line arguments for the frontmatter helper.
    """
    parser = argparse.ArgumentParser(
        description="Helper tool to update YAML frontmatter fields in Markdown documents."
    )
    parser.add_argument("file", type=str, help="Path to the markdown file.")
    parser.add_argument("--status", choices=["draft", "review", "published", "deprecated", "outdated"], help="New status.")
    parser.add_argument(
        "--version-bump",
        choices=["major", "minor", "patch", "publish"],
        help="Bump version. 'publish' sets 0.x drafts to 1.0. 'major' increments x.0, 'minor' increments 1.x, 'patch' increments 1.x.y.",
    )
    parser.add_argument("--approved-by", type=str, help="Approved by role.")
    parser.add_argument("--approved-date", type=str, help="Approved date (YYYY-MM-DD). Defaults to today if publishing.")
    parser.add_argument("--change", type=str, help="Changelog entry text description.")
    parser.add_argument("--owner", type=str, help="Update review_owner.")
    parser.add_argument("--interval", type=int, help="Update review_interval_days.")
    parser.add_argument("--classification", choices=["public", "internal", "confidential", "restricted", "customer confidential"], help="Update classification level.")
    return parser.parse_args()

def bump_version_string(v_str: str, bump_type: str) -> str:
    """
    Increment a semantic-like version string based on bump type:
    - 'publish': converts any 0.x draft version to 1.0.
    - 'major': increments the major digit (X.y.z -> X+1.0.0).
    - 'minor': increments the minor digit (x.Y.z -> x.Y+1.0).
    - 'patch': increments the patch digit (x.y.Z -> x.y.Z+1).
    """
    # Remove quotes if present
    v_str = str(v_str).strip("'\"")
    if bump_type == "publish":
        if v_str.startswith("0."):
            return "1.0"
        return v_str
        
    parts = v_str.split(".")
    try:
        parts_int = [int(p) for p in parts]
    except ValueError:
        # Fallback if version format is non-standard
        return v_str

    if bump_type == "major":
        parts_int[0] += 1
        if len(parts_int) > 1:
            parts_int[1] = 0
        if len(parts_int) > 2:
            parts_int[2] = 0
    elif bump_type == "minor":
        if len(parts_int) > 1:
            parts_int[1] += 1
        else:
            parts_int.append(1)
        if len(parts_int) > 2:
            parts_int[2] = 0
    elif bump_type == "patch":
        if len(parts_int) > 2:
            parts_int[2] += 1
        elif len(parts_int) > 1:
            parts_int.append(1)
        else:
            parts_int.extend([0, 1])
            
    return ".".join(str(p) for p in parts_int)

def main() -> int:
    args = parse_args()
    path = Path(args.file)
    if not path.exists():
        print(f"Error: File {path} not found.")
        return 1

    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        print("Error: Document has no YAML frontmatter prefix.")
        return 1
        
    end_idx = content.find("---", 3)
    if end_idx == -1:
        print("Error: Document has unclosed YAML frontmatter prefix.")
        return 1

    frontmatter_text = content[3:end_idx]
    body_text = content[end_idx:] # includes the closing '---' onwards

    try:
        fm = yaml.safe_load(frontmatter_text) or {}
    except Exception as e:
        print(f"Error parsing YAML frontmatter: {e}")
        return 1

    updated = False
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Update metadata fields
    if args.status:
        fm["status"] = args.status
        updated = True
        
    if args.owner:
        fm["review_owner"] = args.owner
        updated = True

    if args.interval is not None:
        fm["review_interval_days"] = args.interval
        updated = True

    if args.classification:
        fm["classification"] = args.classification
        updated = True

    # Version bumping
    if args.version_bump:
        current_version = str(fm.get("version", "0.1"))
        new_version = bump_version_string(current_version, args.version_bump)
        fm["version"] = new_version
        print(f"Bumped version from {current_version} to {new_version}")
        updated = True

    # Approvals
    if args.approved_by:
        fm["approved_by"] = args.approved_by
        updated = True

    if args.approved_date:
        fm["approved_date"] = args.approved_date
        updated = True
    elif args.status == "published" and not fm.get("approved_date"):
        fm["approved_date"] = today_str
        updated = True

    # Handle status: published review date shifts
    if args.status == "published":
        fm["last_reviewed"] = today_str
        interval = int(fm.get("review_interval_days", 90))
        next_review_dt = datetime.now() + timedelta(days=interval)
        fm["next_review"] = next_review_dt.strftime("%Y-%m-%d")
        print(f"Updated review dates: last_reviewed={fm['last_reviewed']}, next_review={fm['next_review']}")
        updated = True

    # Add changelog entry
    if args.change:
        changelog = fm.get("changelog")
        if not isinstance(changelog, list):
            changelog = []
        entry = {
            "date": today_str,
            "change": args.change
        }
        changelog.insert(0, entry) # prepend to show newest first
        fm["changelog"] = changelog
        print(f"Added changelog entry: {entry}")
        updated = True

    if not updated:
        print("No changes specified. Nothing to do.")
        return 0

    # yaml.safe_dump quotes a value like "1.0" on its own (needed so it
    # round-trips as a string, not a float) — but it uses single quotes
    # ('1.0'), while every hand-written document in this repo uses double
    # quotes ("1.0"). No cleanup step reconciles that; a value this script
    # touches can end up with different quote style than the rest of the
    # file. Not corrected here — flagging so it isn't mistaken for
    # intentional normalization.
    new_fm_text = yaml.safe_dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)
    
    # Write back to file
    new_content = "---\n" + new_fm_text + body_text
    path.write_text(new_content, encoding="utf-8")
    print(f"Successfully updated frontmatter in {path}.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
