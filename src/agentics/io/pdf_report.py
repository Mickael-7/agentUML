from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

_DIMENSION_LABELS = {
    "clarity":       "Clareza",
    "completeness":  "Completude",
    "consistency":   "Consistencia",
    "verifiability": "Verificabilidade",
}
_DIMENSION_ORDER = ["clarity", "completeness", "consistency", "verifiability"]

# Monochrome palette
_BLACK  = (0, 0, 0)
_DARK   = (30, 30, 30)
_MID    = (90, 90, 90)
_LIGHT  = (160, 160, 160)
_RULE   = (200, 200, 200)
_BG     = (245, 245, 245)


def generate_quality_pdf(quality_result: dict[str, Any], output_path: Path) -> Path:
    from fpdf import FPDF

    report      = quality_result.get("report", {})
    summary     = report.get("summary", "")
    suggestions = report.get("suggestions", [])
    today       = date.today().strftime("%d/%m/%Y")

    class PDF(FPDF):
        def header(self):
            pass

        def footer(self):
            self.set_y(-14)
            self.set_draw_color(*_RULE)
            self.set_line_width(0.3)
            self.line(self.l_margin, self.get_y(), self.l_margin + self.w - self.l_margin - self.r_margin, self.get_y())
            self.ln(2)
            self.set_font("Helvetica", "I", 9)
            self.set_text_color(*_LIGHT)
            self.cell(0, 5, f"Relatorio de Qualidade de Requisitos  |  {today}", align="C")

    pdf = PDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    W = pdf.w - pdf.l_margin - pdf.r_margin

    def hrule(thickness: float = 0.3, color=_RULE) -> None:
        pdf.set_draw_color(*color)
        pdf.set_line_width(thickness)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + W, pdf.get_y())
        pdf.ln(5)

    def section_title(text: str) -> None:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_LIGHT)
        pdf.cell(W, 5, text.upper(), ln=True)
        pdf.ln(1)
        hrule(0.3, _RULE)

    # ── Title block ────────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*_BLACK)
    pdf.cell(W, 12, "Relatorio de Qualidade", ln=True)

    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(*_MID)
    pdf.cell(W, 7, "Analise de documento de requisitos para geracao de diagramas UML", ln=True)
    pdf.ln(3)
    hrule(0.6, _DARK)

    # ── Summary ────────────────────────────────────────────────────────────────
    section_title("Resumo Geral")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*_DARK)
    pdf.multi_cell(W, 6, summary)
    pdf.ln(8)

    # ── Dimensions ─────────────────────────────────────────────────────────────
    section_title("Avaliacao por Dimensao")

    for dim in _DIMENSION_ORDER:
        dim_data   = report.get(dim)
        if not dim_data:
            continue
        highlights = dim_data.get("highlights", [])
        issues     = dim_data.get("issues", [])
        label      = _DIMENSION_LABELS.get(dim, dim)

        # Dimension heading
        pdf.set_font("Helvetica", "B", 13)
        pdf.set_text_color(*_BLACK)
        pdf.cell(W, 7, label, ln=True)

        # Highlights sub-block
        if highlights:
            pdf.ln(1)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*_MID)
            pdf.cell(W, 5, "Pontos positivos", ln=True)
            pdf.ln(1)
            for h in highlights:
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(*_DARK)
                pdf.set_x(pdf.l_margin + 5)
                pdf.cell(6, 5.5, "+")
                pdf.set_x(pdf.l_margin + 11)
                pdf.multi_cell(W - 11, 5.5, h)

        # Issues sub-block
        if issues:
            pdf.ln(2 if highlights else 1)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*_MID)
            pdf.cell(W, 5, "Problemas identificados", ln=True)
            pdf.ln(1)
            for issue in issues:
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(*_DARK)
                pdf.set_x(pdf.l_margin + 5)
                pdf.cell(6, 5.5, "-")
                pdf.set_x(pdf.l_margin + 11)
                pdf.multi_cell(W - 11, 5.5, issue)

        if not highlights and not issues:
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(*_LIGHT)
            pdf.set_x(pdf.l_margin + 5)
            pdf.cell(W - 5, 5.5, "Sem observacoes.", ln=True)

        pdf.ln(4)
        # thin divider between dimensions
        pdf.set_draw_color(*_RULE)
        pdf.set_line_width(0.2)
        pdf.line(pdf.l_margin + 2, pdf.get_y(), pdf.l_margin + W, pdf.get_y())
        pdf.ln(5)

    pdf.ln(2)

    # ── Suggestions ────────────────────────────────────────────────────────────
    if suggestions:
        section_title("Sugestoes de Melhoria")
        for i, suggestion in enumerate(suggestions, 1):
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(*_MID)
            pdf.set_x(pdf.l_margin)
            pdf.cell(10, 6, f"{i}.")
            pdf.set_font("Helvetica", "", 11)
            pdf.set_text_color(*_DARK)
            pdf.set_x(pdf.l_margin + 10)
            pdf.multi_cell(W - 10, 6, suggestion)
            pdf.ln(2)

    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    pdf_path = output_path / "quality_report.pdf"
    pdf.output(str(pdf_path))
    return pdf_path


def generate_use_case_eval_pdf(eval_result: dict[str, Any], output_path: Path) -> Path:
    """Render a use-case document evaluation result to a PDF report."""
    from fpdf import FPDF

    summary   = eval_result.get("summary", {})
    documents = eval_result.get("documents", [])
    today     = date.today().strftime("%d/%m/%Y")

    total      = summary.get("total", len(documents))
    evaluated  = summary.get("evaluated", len(documents))
    n_correct  = summary.get("correct", 0)
    n_incorrect = summary.get("incorrect", 0)
    accuracy   = summary.get("accuracy")

    class PDF(FPDF):
        def footer(self):
            self.set_y(-14)
            self.set_draw_color(*_RULE)
            self.set_line_width(0.3)
            self.line(self.l_margin, self.get_y(), self.l_margin + self.w - self.r_margin, self.get_y())
            self.ln(2)
            self.set_font("Helvetica", "I", 9)
            self.set_text_color(*_LIGHT)
            self.cell(0, 5, f"Avaliacao de Casos de Uso  |  {today}", align="C")

    pdf = PDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    W = pdf.w - pdf.l_margin - pdf.r_margin

    def hrule(thickness: float = 0.3, color=_RULE) -> None:
        pdf.set_draw_color(*color)
        pdf.set_line_width(thickness)
        pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + W, pdf.get_y())
        pdf.ln(5)

    def section_title(text: str) -> None:
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*_LIGHT)
        pdf.cell(W, 5, text.upper(), ln=True)
        pdf.ln(1)
        hrule(0.3, _RULE)

    # ── Title block ────────────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(*_BLACK)
    pdf.cell(W, 12, "Avaliacao de Casos de Uso", ln=True)

    pdf.set_font("Helvetica", "", 12)
    pdf.set_text_color(*_MID)
    pdf.cell(W, 7, "Classificacao automatica de documentos (correto/incorreto)", ln=True)
    pdf.ln(3)
    hrule(0.6, _DARK)

    # ── Summary ────────────────────────────────────────────────────────────────
    section_title("Resumo")
    acc_text = "Sem ground truth" if accuracy is None else f"{accuracy}%"
    stats = [
        ("Documentos enviados", str(total)),
        ("Documentos avaliados", str(evaluated)),
        ("Corretos", str(n_correct)),
        ("Incorretos", str(n_incorrect)),
        ("Acuracia (vs. esperado)", acc_text),
    ]
    for label, value in stats:
        pdf.set_font("Helvetica", "", 11)
        pdf.set_text_color(*_MID)
        pdf.cell(W * 0.6, 6.5, label)
        pdf.set_font("Helvetica", "B", 11)
        pdf.set_text_color(*_DARK)
        pdf.cell(W * 0.4, 6.5, value, ln=True)
    pdf.ln(6)

    # ── Per-document sections ──────────────────────────────────────────────────
    section_title("Documentos Avaliados")

    for i, doc in enumerate(documents, 1):
        verdict    = doc.get("verdict", "incorrect")
        checks     = doc.get("checks", {}) or {}
        errors     = doc.get("errors", []) or []
        just       = doc.get("justification", "") or ""
        correction = doc.get("correction", "") or ""
        expected   = doc.get("expected_verdict")
        matches    = doc.get("matches_expected")

        is_correct = verdict == "correct"
        verdict_label = "CORRETO" if is_correct else "INCORRETO"
        verdict_color = _DARK if is_correct else (120, 40, 40)

        # Header line: index + name + verdict
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(*_BLACK)
        pdf.cell(8, 7, f"{i}.")
        pdf.set_font("Helvetica", "B", 12)
        name = str(doc.get("name", f"Documento {i}"))
        name_w = W - 8 - 30
        pdf.cell(name_w, 7, name[:60])
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*verdict_color)
        pdf.cell(30, 7, verdict_label, ln=True, align="R")

        # Ground-truth line (only if labeled)
        if expected is not None:
            match_label = "acerto" if matches else "erro"
            match_color = _MID if matches else (120, 40, 40)
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(*match_color)
            pdf.set_x(pdf.l_margin + 8)
            pdf.cell(W - 8, 5, f"Esperado: {expected}  |  classificacao: {match_label}", ln=True)

        # Checks line
        def _yn(v: Any) -> str:
            if v is None:
                return "n/a"
            return "Sim" if v else "Nao"

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(*_DARK)
        pdf.set_x(pdf.l_margin + 8)
        checks_line = (
            f"Requisito: {_yn(checks.get('has_requirement'))}    "
            f"Contexto UC: {_yn(checks.get('has_use_case_context'))}    "
            f"Simbologia: {_yn(checks.get('symbology_correct'))}"
        )
        pdf.cell(W - 8, 5.5, checks_line, ln=True)

        # Errors
        if errors:
            pdf.ln(1)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*_MID)
            pdf.set_x(pdf.l_margin + 8)
            pdf.cell(W - 8, 5, "Erros", ln=True)
            for err in errors:
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(*_DARK)
                pdf.set_x(pdf.l_margin + 12)
                pdf.cell(6, 5.5, "-")
                pdf.set_x(pdf.l_margin + 18)
                pdf.multi_cell(W - 18, 5.5, str(err))

        # Justification
        if just:
            pdf.ln(1)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*_MID)
            pdf.set_x(pdf.l_margin + 8)
            pdf.cell(W - 8, 5, "Justificativa", ln=True)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*_DARK)
            pdf.set_x(pdf.l_margin + 12)
            pdf.multi_cell(W - 12, 5.5, just)

        # Correction
        if correction:
            pdf.ln(1)
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(*_MID)
            pdf.set_x(pdf.l_margin + 8)
            pdf.cell(W - 8, 5, "Correcao sugerida", ln=True)
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(*_DARK)
            pdf.set_x(pdf.l_margin + 12)
            pdf.multi_cell(W - 12, 5.5, correction)

        pdf.ln(5)
        pdf.set_draw_color(*_RULE)
        pdf.set_line_width(0.2)
        pdf.line(pdf.l_margin + 2, pdf.get_y(), pdf.l_margin + W, pdf.get_y())
        pdf.ln(5)

    output_path = Path(output_path)
    output_path.mkdir(parents=True, exist_ok=True)
    pdf_path = output_path / "use_case_evaluation.pdf"
    pdf.output(str(pdf_path))
    return pdf_path
