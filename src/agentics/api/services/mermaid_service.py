from __future__ import annotations

from agentics.parser.puml_lite import PumlParser


class MermaidConverter:
    def __init__(self) -> None:
        self._parser = PumlParser()

    def convert(self, puml_text: str, diagram_type: str) -> str:
        if diagram_type == "use_case":
            return self._convert_use_case(puml_text)
        elif diagram_type in ("domain_class", "specialized_class"):
            return self._convert_class(puml_text)
        elif diagram_type == "sequence":
            return self._convert_sequence(puml_text)
        return ""

    def _convert_use_case(self, text: str) -> str:
        elements = self._parser.parse_elements(text, "use_case")
        lines = ["graph LR"]
        for uc in elements.use_cases:
            safe_id = uc.alias.replace(" ", "_")
            lines.append(f'    {safe_id}["{uc.display_name}"]')
        for actor in elements.actors:
            safe_id = actor.alias.replace(" ", "_")
            lines.append(f'    {safe_id}(["{actor.display_name}"])')
        return "\n".join(lines)

    def _convert_class(self, text: str) -> str:
        elements = self._parser.parse_elements(text, "domain_class")
        lines = ["classDiagram"]
        for cls in elements.classes:
            lines.append(f"    class {cls.display_name} {{")
            for attr in cls.attributes:
                lines.append(f"        {attr}")
            for method in cls.methods:
                lines.append(f"        {method}")
            lines.append("    }")
        return "\n".join(lines)

    def _convert_sequence(self, text: str) -> str:
        elements = self._parser.parse_elements(text, "sequence")
        lines = ["sequenceDiagram"]
        for ll in elements.lifelines:
            lines.append(f"    participant {ll.alias} as {ll.display_name}")
        for msg in elements.messages:
            arrow = "->>" if "->" in msg.arrow else "->"
            lines.append(f"    {msg.source}{arrow}{msg.target}: {msg.text}")
        return "\n".join(lines)
