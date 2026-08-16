---
name: link-check
description: Local link checking utility to verify the integrity of relative document link references in all Markdown files.
---

# Skill: link-check

This skill provides a local Python link checking script [`link_checker.py`](./link_checker.py) that scans the repository and validates all relative internal links to verify integrity without waiting for slow external tools.

## Running the checker

Run the tool locally in the workspace:

```bash
python3 skills/link-check/link_checker.py
```
