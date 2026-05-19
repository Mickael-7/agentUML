from __future__ import annotations

import re
from dataclasses import dataclass, field


class MetadataParseError(Exception):
    pass


@dataclass
class Actor:
    alias: str
    display_name: str
    stereotype: str = ""


@dataclass
class UseCase:
    alias: str
    display_name: str
    req_ref: str = ""


@dataclass
class Class:
    alias: str
    display_name: str
    stereotype: str = ""
    attributes: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)


@dataclass
class Lifeline:
    alias: str
    display_name: str
    lifeline_type: str = "participant"


@dataclass
class Message:
    source: str
    target: str
    text: str
    arrow: str = "->"


@dataclass
class PumlElements:
    actors: list[Actor] = field(default_factory=list)
    use_cases: list[UseCase] = field(default_factory=list)
    classes: list[Class] = field(default_factory=list)
    lifelines: list[Lifeline] = field(default_factory=list)
    messages: list[Message] = field(default_factory=list)


_METADATA_START = re.compile(r"'\s*===\s*AGENTICS METADATA\s*===")
_METADATA_END = re.compile(r"'\s*===\s*END METADATA\s*===")
_META_FIELD = re.compile(r"'\s*(\w+):\s*(.+)")
_REQ_LIST = re.compile(r"\[([^\]]*)\]")

_ACTOR_RE = re.compile(r'^actor\s+"([^"]+)"\s+as\s+(\w+)(?:\s+<<([^>]+)>>)?', re.MULTILINE)
_UC_RE = re.compile(r'^usecase\s+"([^"]+)"\s+as\s+(\w+)(?:\s+<<\s*req:(\w+)\s*>>)?', re.MULTILINE)
_CLASS_START_RE = re.compile(
    r'^class\s+"([^"]+)"\s+as\s+(\w+)(?:\s+<<([^>]+)>>)?\s*\{', re.MULTILINE
)
_LIFELINE_RE = re.compile(
    r'^(actor|boundary|control|entity|participant)\s+"([^"]+)"\s+as\s+(\w+)', re.MULTILINE
)
_MESSAGE_RE = re.compile(r"^(\w+)\s+(->+|-->+|->?>)\s+(\w+)\s*(?::\s*(.*))?$", re.MULTILINE)
_ATTR_RE = re.compile(
    r"^\s*[-+#~]?\s*(?:\{[^}]+\}\s*)?(\w+)\s*:",
)
_METHOD_RE = re.compile(r"^\s*[-+#~]\s*(?:\{[^}]+\}\s*)?\w+\s*\(")


class PumlParser:
    def parse_metadata(self, puml_text: str) -> dict:
        lines = puml_text.splitlines()
        in_block = False
        fields: dict[str, str | list] = {}

        for line in lines:
            if _METADATA_START.search(line):
                in_block = True
                continue
            if _METADATA_END.search(line):
                break
            if in_block:
                m = _META_FIELD.match(line)
                if m:
                    key, value = m.group(1).strip(), m.group(2).strip()
                    if key == "source_requirements":
                        rm = _REQ_LIST.search(value)
                        if rm:
                            fields[key] = [r.strip() for r in rm.group(1).split(",") if r.strip()]
                        else:
                            fields[key] = []
                    else:
                        fields[key] = value

        required = {"diagram_id", "diagram_type", "name", "source_requirements"}
        missing = required - fields.keys()
        if missing:
            raise MetadataParseError(
                f"Missing required metadata fields: {', '.join(sorted(missing))}"
            )
        return fields

    def parse_elements(self, puml_text: str, diagram_type: str) -> PumlElements:
        elements = PumlElements()
        if diagram_type == "use_case":
            elements.actors = self._parse_actors(puml_text)
            elements.use_cases = self._parse_use_cases(puml_text)
        elif diagram_type in {"domain_class", "specialized_class"}:
            elements.classes = self._parse_classes(puml_text)
        elif diagram_type == "sequence":
            elements.lifelines = self._parse_lifelines(puml_text)
            elements.messages = self._parse_messages(puml_text)
        return elements

    def _parse_actors(self, text: str) -> list[Actor]:
        return [
            Actor(alias=m.group(2), display_name=m.group(1), stereotype=m.group(3) or "")
            for m in _ACTOR_RE.finditer(text)
        ]

    def _parse_use_cases(self, text: str) -> list[UseCase]:
        return [
            UseCase(alias=m.group(2), display_name=m.group(1), req_ref=m.group(3) or "")
            for m in _UC_RE.finditer(text)
        ]

    def _parse_classes(self, text: str) -> list[Class]:
        classes = []
        for m in _CLASS_START_RE.finditer(text):
            display_name = m.group(1)
            alias = m.group(2)
            stereotype = m.group(3) or ""
            # Extract body between the opening { and the matching }
            start = m.end()
            depth = 1
            pos = start
            while pos < len(text) and depth > 0:
                if text[pos] == "{":
                    depth += 1
                elif text[pos] == "}":
                    depth -= 1
                pos += 1
            body = text[start : pos - 1]
            attrs = []
            methods = []
            for line in body.splitlines():
                if _METHOD_RE.match(line):
                    methods.append(line.strip())
                elif _ATTR_RE.match(line) and line.strip():
                    attrs.append(line.strip())
            classes.append(
                Class(
                    alias=alias,
                    display_name=display_name,
                    stereotype=stereotype,
                    attributes=attrs,
                    methods=methods,
                )
            )
        return classes

    def _parse_lifelines(self, text: str) -> list[Lifeline]:
        return [
            Lifeline(
                alias=m.group(3),
                display_name=m.group(2),
                lifeline_type=m.group(1),
            )
            for m in _LIFELINE_RE.finditer(text)
        ]

    def _parse_messages(self, text: str) -> list[Message]:
        return [
            Message(
                source=m.group(1),
                target=m.group(3),
                arrow=m.group(2),
                text=m.group(4) or "",
            )
            for m in _MESSAGE_RE.finditer(text)
        ]
