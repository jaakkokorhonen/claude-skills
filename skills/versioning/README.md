# Skill: versioning

Full content lives in [`SKILL.md`](./SKILL.md) - that file is the one Claude/Anthropic Agent Skills loads (it carries the required `name`/`description` frontmatter) and is also the canonical, human-readable copy. This README is intentionally just a pointer: `README.md` and `SKILL.md` used to contain the same content twice (plus a third, byte-identical `versioning.md` which has been deleted) - three places to keep in sync on every edit. Read `SKILL.md` directly; do not duplicate its content back into this file.

See also:
- [`release_tagger.py`](./release_tagger.py) - release-tagging automation referenced in `SKILL.md`'s "Release Tagging" section.
- [`frontmatter_helper.py`](./frontmatter_helper.py) - frontmatter metadata helper utility for automated version bumps and date calculation.
