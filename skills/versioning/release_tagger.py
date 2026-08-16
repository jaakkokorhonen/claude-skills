#!/usr/bin/env python3
"""
release_tagger.py
Automates Git tag creation for published compliance documents and SOP batches,
satisfying ISO 27001 Clause 7.5.3 documentation controls.
"""
import subprocess
import sys
import yaml
from pathlib import Path
from datetime import datetime

def run_git(args: list[str]) -> str:
    res = subprocess.run(["git"] + args, capture_output=True, text=True, check=True)
    return res.stdout.strip()

def extract_frontmatter(file_path: Path) -> dict:
    if not file_path.exists():
        return {}
    content = file_path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return {}
    end = content.find("---", 3)
    if end == -1:
        return {}
    try:
        return yaml.safe_load(content[3:end]) or {}
    except Exception:
        return {}

def main() -> int:
    print("Running versioning skill release tagger...")
    
    # Get modified/added markdown files in the last commit/HEAD
    try:
        changed_files_raw = run_git(["diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD"])
        changed_files = [Path(line) for line in changed_files_raw.splitlines() if line.endswith(".md")]
    except Exception as e:
        print(f"Error checking git diff: {e}")
        return 1

    if not changed_files:
        print("No Markdown files modified in the latest commit.")
        return 0

    today_str = datetime.now().strftime("%Y-%m-%d")
    year_month_str = datetime.now().strftime("%Y.%m")
    
    compliance_published = []
    sops_published = []

    for path in changed_files:
        fm = extract_frontmatter(path)
        if not fm:
            continue
            
        status = fm.get("status")
        doc_type = fm.get("type")
        
        if status == "published":
            # "dpia" is not a valid `type` value (CONTRIBUTING.md's enum is
            # sop/guide/appendix/template/policy — document_validator.py
            # enforces this, and DPIA.md itself uses type: policy). That
            # half of this check can never match; kept only as a defensive
            # no-op in case a document is ever mistagged, same call made in
            # document_validator.py's own now-fixed version of this check.
            # The filename checks below are what actually catch DPIA.md /
            # ISO-27001-Audit.md.
            if doc_type in ("policy", "dpia") or path.name == "DPIA.md" or path.name == "ISO-27001-Audit.md":
                compliance_published.append(path)
            elif doc_type == "sop":
                sops_published.append(path)

    tags_to_create = []

    # 1. Compliance snapshot tag (if any policy/dpia became published)
    if compliance_published:
        tag_name = f"compliance/{today_str}"
        tags_to_create.append((tag_name, f"Compliance snapshots published: {[p.name for p in compliance_published]}"))

    # 2. Ops snapshot tag (if any SOPs became published)
    if sops_published:
        tag_name = f"ops/v{year_month_str}"
        tags_to_create.append((tag_name, f"Ops SOPs published: {[p.name for p in sops_published]}"))

    if not tags_to_create:
        print("No compliance or SOP documents promoted to 'published' in this commit. No tagging needed.")
        return 0

    for tag, msg in tags_to_create:
        print(f"Creating tag: {tag} ({msg})")
        try:
            # Check if tag already exists
            existing = run_git(["tag", "-l", tag])
            if existing == tag:
                print(f"Tag {tag} already exists. Skipping.")
                continue
                
            # Create annotated tag
            subprocess.run(["git", "tag", "-a", tag, "-m", msg], check=True)
            print(f"Successfully created local tag {tag}.")
            print(f"To push: git push origin {tag}")
        except Exception as e:
            print(f"Failed to create tag {tag}: {e}")
            return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
