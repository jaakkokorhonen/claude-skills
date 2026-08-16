"""Unit tests for extract_frontmatter()."""
from document_validator import extract_frontmatter


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

def test_valid_frontmatter_returns_dict():
    text = "---\ntitle: Hello\nstatus: draft\n---\nBody text"
    fm, warnings = extract_frontmatter(text)
    assert fm == {"title": "Hello", "status": "draft"}
    assert warnings == []


def test_no_warnings_on_clean_file():
    text = "---\ntitle: Test\n---\n"
    _, warnings = extract_frontmatter(text)
    assert warnings == []


# ---------------------------------------------------------------------------
# Missing / malformed frontmatter
# ---------------------------------------------------------------------------

def test_missing_frontmatter_returns_none():
    fm, errors = extract_frontmatter("# Just a heading\nNo frontmatter")
    assert fm is None
    assert any("must start with" in e for e in errors)


def test_unclosed_frontmatter_returns_none():
    fm, errors = extract_frontmatter("---\ntitle: Hello\n")
    assert fm is None
    assert any("no closing" in e for e in errors)


def test_invalid_yaml_returns_none():
    fm, errors = extract_frontmatter("---\nkey: [unclosed\n---\n")
    assert fm is None
    assert any("YAML parse error" in e for e in errors)


def test_non_mapping_yaml_returns_none():
    fm, errors = extract_frontmatter("---\n- list item\n---\n")
    assert fm is None
    assert any("YAML mapping" in e for e in errors)


# ---------------------------------------------------------------------------
# Marp double-frontmatter detection
# ---------------------------------------------------------------------------

def test_marp_duplicate_block_raises_warning():
    text = "---\ntitle: T\n---\n---\nmarp: true\n---\n"
    _, warnings = extract_frontmatter(text)
    assert any("DUPLICATE FRONTMATTER" in w for w in warnings)


def test_single_block_with_marp_key_no_warning():
    """marp: true inside the single frontmatter block is valid."""
    text = "---\ntitle: T\nmarp: true\n---\nContent"
    _, warnings = extract_frontmatter(text)
    assert warnings == []


def test_body_opening_with_horizontal_rule_no_false_positive():
    """A body whose first line is a Markdown horizontal rule ("---") is not
    a second frontmatter block and must not be flagged as duplicate.
    Regression test: the previous implementation matched on the bare "---"
    token, which fired here even though nothing after it parses as YAML."""
    text = "---\ntitle: T\n---\n\n---\n\nSome text below the rule.\n"
    _, warnings = extract_frontmatter(text)
    assert warnings == []


def test_body_with_two_rules_but_no_yaml_between_no_false_positive():
    """Two horizontal rules with plain prose between them (not a YAML
    mapping) must not be flagged either."""
    text = "---\ntitle: T\n---\n---\nJust some prose, not a mapping.\n---\n"
    _, warnings = extract_frontmatter(text)
    assert warnings == []
