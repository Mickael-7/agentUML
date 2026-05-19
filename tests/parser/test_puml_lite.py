import pytest

from agentics.parser.puml_lite import MetadataParseError, PumlParser

VALID_UC = """
@startuml
' === AGENTICS METADATA ===
' diagram_id: uc_1
' diagram_type: use_case
' name: Gestão de Autenticação
' source_requirements: [req1, req2]
' === END METADATA ===

left to right direction

actor "Usuário"       as ator_usuario  <<primary>>
actor "Administrador" as ator_admin    <<secondary>>

usecase "Realizar Login"      as uc_login   << req:req1 >>
usecase "Validar Credenciais" as uc_validar << req:req2 >>

ator_usuario --> uc_login
uc_login ..> uc_validar : <<include>>
@enduml
"""

VALID_DOMAIN = """
@startuml
' === AGENTICS METADATA ===
' diagram_id: domain_1
' diagram_type: domain_class
' name: Domínio de Autenticação
' source_requirements: [req1, req2]
' === END METADATA ===

class "Usuario" as cls_usuario <<entity>> {
  - id: UUID
  - email: String
}

class "Sessao" as cls_sessao <<entity>> {
  - id: UUID
  - expira_em: DateTime
}

cls_usuario "1" -- "0..*" cls_sessao : possui
@enduml
"""

VALID_SEQUENCE = """
@startuml
' === AGENTICS METADATA ===
' diagram_id: seq_1
' diagram_type: sequence
' name: Fluxo de Login
' source_requirements: [req1, req2]
' related_use_case: uc_login
' === END METADATA ===

actor   "Usuário"        as ll_usuario
control "AuthController" as ll_controller
entity  "Usuario"        as ll_usuario_obj

ll_usuario -> ll_controller : login(email, senha)
ll_controller -> ll_usuario_obj : validar(senha)
ll_usuario_obj --> ll_controller : ok
ll_controller --> ll_usuario : token
@enduml
"""

NO_METADATA = "@startuml\nactor X as ator_x\n@enduml"
MISSING_FIELD = """
@startuml
' === AGENTICS METADATA ===
' diagram_id: uc_1
' diagram_type: use_case
' === END METADATA ===
@enduml
"""


def test_parse_metadata_valid():
    parser = PumlParser()
    meta = parser.parse_metadata(VALID_UC)
    assert meta["diagram_id"] == "uc_1"
    assert meta["diagram_type"] == "use_case"
    assert meta["name"] == "Gestão de Autenticação"
    assert meta["source_requirements"] == ["req1", "req2"]


def test_parse_metadata_optional_fields():
    parser = PumlParser()
    meta = parser.parse_metadata(VALID_SEQUENCE)
    assert meta["related_use_case"] == "uc_login"


def test_parse_metadata_missing_header():
    parser = PumlParser()
    with pytest.raises(MetadataParseError):
        parser.parse_metadata(NO_METADATA)


def test_parse_metadata_missing_field():
    parser = PumlParser()
    with pytest.raises(MetadataParseError, match="name"):
        parser.parse_metadata(MISSING_FIELD)


def test_parse_elements_use_case():
    parser = PumlParser()
    elements = parser.parse_elements(VALID_UC, "use_case")
    assert len(elements.actors) == 2
    assert elements.actors[0].alias == "ator_usuario"
    assert elements.actors[0].stereotype == "primary"
    assert len(elements.use_cases) == 2
    assert elements.use_cases[0].alias == "uc_login"


def test_parse_elements_domain():
    parser = PumlParser()
    elements = parser.parse_elements(VALID_DOMAIN, "domain_class")
    assert len(elements.classes) == 2
    cls = elements.classes[0]
    assert cls.alias == "cls_usuario"
    assert cls.display_name == "Usuario"
    assert len(cls.methods) == 0  # domain has no methods


def test_parse_elements_sequence():
    parser = PumlParser()
    elements = parser.parse_elements(VALID_SEQUENCE, "sequence")
    aliases = [ll.alias for ll in elements.lifelines]
    assert "ll_usuario" in aliases
    assert "ll_controller" in aliases
    assert len(elements.messages) >= 2
