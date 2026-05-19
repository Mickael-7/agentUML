import pytest

from agentics.io.reader import DocumentReader, UnsupportedFormatError


def test_read_markdown(tmp_path):
    md = tmp_path / "req.md"
    md.write_text("# Requirements\n\nreq1: user can login", encoding="utf-8")
    reader = DocumentReader()
    content = reader.read(str(md))
    assert "req1" in content


def test_unsupported_format():
    reader = DocumentReader()
    with pytest.raises(UnsupportedFormatError, match="xlsx"):
        reader.read("requirements.xlsx")


def test_read_text_file(tmp_path):
    txt = tmp_path / "req.txt"
    txt.write_text("plain text requirement", encoding="utf-8")
    reader = DocumentReader()
    assert "plain text" in reader.read(str(txt))
