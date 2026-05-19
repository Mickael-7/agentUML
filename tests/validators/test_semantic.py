from agentics.validators.semantic import SemanticValidator, cross_validate

VALID_UC = """
@startuml
' === AGENTICS METADATA ===
' diagram_id: uc_1
' diagram_type: use_case
' name: Auth
' source_requirements: [req1]
' === END METADATA ===
left to right direction
actor "Usuário" as ator_usuario <<primary>>
usecase "Login" as uc_login << req:req1 >>
ator_usuario --> uc_login
@enduml
"""

UNDECLARED_ACTOR_UC = """
@startuml
' === AGENTICS METADATA ===
' diagram_id: uc_1
' diagram_type: use_case
' name: Auth
' source_requirements: [req1]
' === END METADATA ===
ator_admin --> uc_login
@enduml
"""

DOMAIN_WITH_METHOD = """
@startuml
' === AGENTICS METADATA ===
' diagram_id: domain_1
' diagram_type: domain_class
' name: Auth
' source_requirements: [req1]
' === END METADATA ===
class "Usuario" as cls_usuario <<entity>> {
  - id: UUID
  + autenticar(): bool
}
@enduml
"""

VALID_DOMAIN = """
@startuml
' === AGENTICS METADATA ===
' diagram_id: domain_1
' diagram_type: domain_class
' name: Auth
' source_requirements: [req1]
' === END METADATA ===
class "Usuario" as cls_usuario <<entity>> {
  - id: UUID
  - email: String
}
@enduml
"""

NO_METADATA = """
@startuml
actor "X" as ator_x <<primary>>
@enduml
"""


def test_valid_use_case_passes():
    v = SemanticValidator()
    result = v.validate(VALID_UC, "use_case")
    assert result.is_valid


def test_undeclared_actor_fails():
    v = SemanticValidator()
    result = v.validate(UNDECLARED_ACTOR_UC, "use_case")
    assert not result.is_valid
    assert any("undeclared_actor" in e.rule for e in result.errors)


def test_domain_with_method_fails():
    v = SemanticValidator()
    result = v.validate(DOMAIN_WITH_METHOD, "domain_class")
    assert not result.is_valid
    assert any("domain_no_methods" in e.rule for e in result.errors)


def test_valid_domain_passes():
    v = SemanticValidator()
    result = v.validate(VALID_DOMAIN, "domain_class")
    assert result.is_valid


def test_missing_metadata_fails():
    v = SemanticValidator()
    result = v.validate(NO_METADATA, "use_case")
    assert not result.is_valid
    assert any("metadata" in e.rule for e in result.errors)


def test_cross_validate_no_inconsistencies():
    domain = {
        "diagram_id": "domain_1",
        "diagram_type": "domain_class",
        "puml_text": VALID_DOMAIN,
    }
    report = cross_validate([domain])
    assert report.inconsistencies == []


def test_cross_validate_missing_class_in_domain():
    seq = {
        "diagram_id": "seq_1",
        "diagram_type": "sequence",
        "puml_text": """
@startuml
' === AGENTICS METADATA ===
' diagram_id: seq_1
' diagram_type: sequence
' name: Test
' source_requirements: [req1]
' === END METADATA ===
entity "PagamentoService" as ll_pag
actor  "Cliente"          as ll_cli
ll_cli -> ll_pag : pagar()
@enduml
""",
    }
    report = cross_validate([seq])
    assert any(i["kind"] == "missing_domain_class" for i in report.inconsistencies)


def test_cross_validate_report_markdown_no_issues():
    report = cross_validate([])
    md = report.to_markdown()
    assert "Sem inconsistências" in md
