#!/usr/bin/env python3
"""
link_checker.py
Scans Markdown files and validates all relative internal links to verify integrity,
without relying on external tool dependencies or running CI.
"""
import re
import sys
from pathlib import Path

def should_exclude(path: Path) -> bool:
    """
    Determine if a file path should be excluded from link validation.
    Skips any path with a dot-prefixed component (e.g. .git/) and anything
    under a 'skills/' directory (this skill's own meta-docs).
    """
    parts = path.parts
    if any(part.startswith(".") for part in parts):
        return True
    if "skills" in parts:
        return True
    return False

def extract_links(text: str) -> list[tuple[int, str]]:
    """
    Parse a Markdown string and extract all relative internal file links.
    Returns a list of tuples containing (line_number, link_url).
    Web URL links, email addresses, and same-page anchor tags are ignored.
    """
    # Simple regex for markdown links: [text](link)
    pattern = r"\[[^\]]*\]\(([^)]+)\)"
    links = []
    for i, line in enumerate(text.splitlines(), 1):
        for match in re.finditer(pattern, line):
            link = match.group(1).strip()
            # Skip web links, mails, anchors within the same page
            if (
                link.startswith("http://")
                or link.startswith("https://")
                or link.startswith("mailto:")
                or link.startswith("#")
            ):
                continue
            links.append((i, link))
    return links

def main() -> int:
    root = Path(".").resolve()
    files = sorted(root.rglob("*.md"))
    total_checked = 0
    broken_count = 0
    
    print("Running link-check utility...")
    for f in files:
        if should_exclude(f.relative_to(root)):
            continue
            
        content = f.read_text(encoding="utf-8")
        links = extract_links(content)
        total_checked += len(links)
        
        file_dir = f.parent
        file_broken = []
        for line_num, link in links:
            # Strip anchor part
            path_part = link.split("#")[0]
            if not path_part:
                continue
            
            # Resolve target path relative to current file's directory
            target_path = (file_dir / path_part).resolve()
            
            # Check if resolved path exists
            if not target_path.exists():
                file_broken.append((line_num, link, target_path))
                broken_count += 1
                
        if file_broken:
            print(f"\n❌ Broken links in {f.relative_to(root)}:")
            for line_num, link, target in file_broken:
                try:
                    rel_target = target.relative_to(root)
                except ValueError:
                    rel_target = target
                print(f"   Line {line_num}: Link '{link}' resolves to non-existent '{rel_target}'")
                
    if broken_count > 0:
        print(f"\nCompleted check: found {broken_count} broken link(s) out of {total_checked} total links.")
        return 1
        
    print(f"OK: Checked {total_checked} relative link(s). No broken links found.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
