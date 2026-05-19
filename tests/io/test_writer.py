from unittest.mock import MagicMock

from agentics.io.writer import DiagramWriter


def _make_writer(tmp_path):
    cfg = MagicMock()
    cfg.output_dir = tmp_path
    return DiagramWriter(cfg)


def test_write_puml_approved(tmp_path):
    writer = _make_writer(tmp_path)
    path = writer.write_puml("uc_1", "@startuml\n@enduml", draft=False)
    assert path.name == "uc_1.puml"
    assert path.exists()


def test_write_puml_draft(tmp_path):
    writer = _make_writer(tmp_path)
    path = writer.write_puml("domain_2", "@startuml\n@enduml", draft=True)
    assert path.name == "domain_2.draft.puml"
    assert path.exists()


def test_write_report(tmp_path):
    writer = _make_writer(tmp_path)
    path = writer.write_report("cross_validation_report.md", "# Report\nOK")
    assert path.name == "cross_validation_report.md"
    assert "Report" in path.read_text()


def test_output_dir_created_automatically(tmp_path):
    nested = tmp_path / "deep" / "output"
    cfg = MagicMock()
    cfg.output_dir = nested
    DiagramWriter(cfg)
    assert nested.exists()
