from __future__ import annotations

import re
from dataclasses import dataclass, field

from agentics.parser.puml_lite import PumlParser


@dataclass
class SemanticError:
    rule: str
    message: str


@dataclass
class SemanticResult:
    is_valid: bool
    errors: list[SemanticError] = field(default_factory=list)

    def add_error(self, rule: str, message: str) -> None:
        self.errors.append(SemanticError(rule=rule, message=message))
        self.is_valid = False


@dataclass
class CrossValidationReport:
    inconsistencies: list[dict] = field(default_factory=list)

    def add(self, kind: str, message: str, source_id: str, target_id: str = "") -> None:
        self.inconsistencies.append(
            {"kind": kind, "message": message, "source": source_id, "target": target_id}
        )

    def to_markdown(self) -> str:
        if not self.inconsistencies:
            return "# Cross-Diagram Validation Report\n\nSem inconsistências detectadas.\n"
        lines = ["# Cross-Diagram Validation Report\n"]
        for item in self.inconsistencies:
            lines.append(
                f"- **[{item['kind']}]** {item['message']} "
                f"(source: `{item['source']}`, target: `{item['target']}`)"
            )
        return "\n".join(lines) + "\n"


_METHOD_LINE = re.compile(r"^\s*[-+#~]\s*(?:\{[^}]+\}\s*)?\w+\s*\(", re.MULTILINE)
_METADATA_BLOCK = re.compile(r"'\s*===\s*AGENTICS METADATA\s*===")
_ACTOR_DECL = re.compile(r'^actor\s+"[^"]+"\s+as\s+(\w+)', re.MULTILINE)
_ACTOR_REF = re.compile(r"^(\w+)\s+-->", re.MULTILINE)
_LL_DECL = re.compile(
    r'^(?:actor|boundary|control|entity|participant)\s+"[^"]+"\s+as\s+(\w+)', re.MULTILINE
)
_LL_REF = re.compile(r"^(\w+)\s+(?:->+|-->+)\s+(\w+)", re.MULTILINE)


class SemanticValidator:
    def __init__(self) -> None:
        self._parser = PumlParser()

    def validate(self, puml_text: str, diagram_type: str) -> SemanticResult:
        result = SemanticResult(is_valid=True)

        if not _METADATA_BLOCK.search(puml_text):
            result.add_error("metadata", "Missing required AGENTICS METADATA block")

        if diagram_type == "use_case":
            self._validate_use_case(puml_text, result)
        elif diagram_type == "domain_class":
            self._validate_domain(puml_text, result)
        elif diagram_type == "sequence":
            self._validate_sequence(puml_text, result)

        return result

    def _validate_use_case(self, text: str, result: SemanticResult) -> None:
        declared = set(_ACTOR_DECL.findall(text))
        for ref in _ACTOR_REF.findall(text):
            if ref not in declared:
                result.add_error(
                    "undeclared_actor",
                    f"Actor alias '{ref}' used in relationship but never declared",
                )

    def _validate_domain(self, text: str, result: SemanticResult) -> None:
        if _METHOD_LINE.search(text):
            result.add_error(
                "domain_no_methods",
                "Domain diagram must not contain method definitions (only attributes allowed)",
            )

    def _validate_sequence(self, text: str, result: SemanticResult) -> None:
        declared = set(_LL_DECL.findall(text))
        for src, tgt in _LL_REF.findall(text):
            for alias in (src, tgt):
                if alias not in declared:
                    result.add_error(
                        "undeclared_lifeline",
                        f"Lifeline alias '{alias}' used in message but never declared",
                    )


def cross_validate(diagrams: list[dict]) -> CrossValidationReport:
    """
    diagrams: list of dicts with keys: diagram_id, diagram_type, puml_text
    """
    report = CrossValidationReport()

    # Build lookup maps
    domain_class_names: set[str] = set()
    uc_actor_names: set[str] = set()
    seq_participant_names: set[str] = set()

    parser = PumlParser()

    domain_pumls: list[dict] = []
    seq_pumls: list[dict] = []
    uc_pumls: list[dict] = []
    spec_pumls: list[dict] = []

    for d in diagrams:
        dt = d.get("diagram_type", "")
        if dt == "domain_class":
            domain_pumls.append(d)
        elif dt == "sequence":
            seq_pumls.append(d)
        elif dt == "use_case":
            uc_pumls.append(d)
        elif dt == "specialized_class":
            spec_pumls.append(d)

    for d in domain_pumls:
        elements = parser.parse_elements(d["puml_text"], "domain_class")
        for cls in elements.classes:
            domain_class_names.add(_normalize(cls.display_name))

    for d in uc_pumls:
        elements = parser.parse_elements(d["puml_text"], "use_case")
        for actor in elements.actors:
            uc_actor_names.add(_normalize(actor.display_name))

    for d in seq_pumls:
        elements = parser.parse_elements(d["puml_text"], "sequence")
        for ll in elements.lifelines:
            seq_participant_names.add(_normalize(ll.display_name))

    # Rule: entity lifelines in sequences must have a matching domain class
    for d in seq_pumls:
        elements = parser.parse_elements(d["puml_text"], "sequence")
        for ll in elements.lifelines:
            if (
                ll.lifeline_type in {"entity", "control", "boundary"}
                and _normalize(ll.display_name) not in domain_class_names
            ):
                report.add(
                    kind="missing_domain_class",
                    message=(
                        f"Lifeline '{ll.display_name}' in sequence "
                        "has no matching class in any domain diagram"
                    ),
                    source_id=d["diagram_id"],
                )

    # Rule: UC actors should appear as participant in at least one sequence
    for d in uc_pumls:
        elements = parser.parse_elements(d["puml_text"], "use_case")
        for actor in elements.actors:
            if _normalize(actor.display_name) not in seq_participant_names:
                report.add(
                    kind="actor_missing_in_sequence",
                    message=(
                        f"Actor '{actor.display_name}' from use case diagram "
                        "does not appear in any sequence diagram"
                    ),
                    source_id=d["diagram_id"],
                )

    # Rule: specialization classes must originate in domain
    for d in spec_pumls:
        elements = parser.parse_elements(d["puml_text"], "specialized_class")
        for cls in elements.classes:
            if _normalize(cls.display_name) not in domain_class_names:
                report.add(
                    kind="spec_class_no_domain_origin",
                    message=(
                        f"Specialized class '{cls.display_name}' "
                        "has no origin class in any domain diagram"
                    ),
                    source_id=d["diagram_id"],
                )

    return report


def _normalize(name: str) -> str:
    return name.strip().lower()
