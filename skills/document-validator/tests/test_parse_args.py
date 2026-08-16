"""Unit tests for parse_args()."""
import pytest

from document_validator import __version__, parse_args


def test_parse_args_default_path():
    args = parse_args([])
    assert args.path == "."


def test_parse_args_explicit_path():
    args = parse_args(["some/dir"])
    assert args.path == "some/dir"


def test_parse_args_version_exits_zero(capsys):
    with pytest.raises(SystemExit) as exc_info:
        parse_args(["--version"])
    assert exc_info.value.code == 0
    out = capsys.readouterr().out
    assert __version__ in out
